"""hr/views.py — Employee, Attendance, Leave, Payroll"""
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from core.models import AuditLog
from .models import (Employee, JobPosition, WorkSchedule, Attendance,
                     LeaveType, LeaveBalance, LeaveRequest,
                     PayrollComponent, Payroll, PayrollDetail, PayrollItem)
from .forms import (EmployeeForm, AttendanceForm, LeaveRequestForm,
                    PayrollForm, PayrollItemForm)


def require_company(view_func):
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.company:
            return redirect('core:select_company')
        return view_func(request, *args, **kwargs)
    return wrapper


# ── EMPLOYEE ─────────────────────────────────────────────────────────────────

@login_required
@require_company
def employee_list(request):
    company = request.company
    q = request.GET.get('q', '').strip()
    dept = request.GET.get('dept', '')
    status = request.GET.get('status', '')

    qs = Employee.objects.filter(
        company=company, resign_date__isnull=True
    ).select_related('department', 'position', 'branch')

    if q:
        qs = qs.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q) |
            Q(employee_id__icontains=q) | Q(email__icontains=q)
        )
    if dept:
        qs = qs.filter(department_id=dept)
    if status:
        qs = qs.filter(employment_status=status)

    page = Paginator(qs.order_by('first_name'), 25).get_page(request.GET.get('page', 1))

    from organization.models import Department
    departments = Department.objects.filter(company=company, is_active=True)

    stats = {
        'total': Employee.objects.filter(company=company, resign_date__isnull=True).count(),
        'permanent': Employee.objects.filter(company=company, resign_date__isnull=True, employment_status='PERMANENT').count(),
        'contract': Employee.objects.filter(company=company, resign_date__isnull=True, employment_status='CONTRACT').count(),
        'probation': Employee.objects.filter(company=company, resign_date__isnull=True, employment_status='PROBATION').count(),
    }

    return render(request, 'hr/employee_list.html', {
        'page_title': 'Karyawan', 'employees': page,
        'q': q, 'selected_dept': dept, 'selected_status': status,
        'departments': departments,
        'employment_statuses': Employee.EmploymentStatus.choices,
        'stats': stats,
    })


@login_required
@require_company
def employee_detail(request, uid):
    emp = get_object_or_404(Employee, uid=uid, company=request.company)
    today = timezone.now().date()
    month_start = today.replace(day=1)

    # Kehadiran bulan ini
    attendances = Attendance.objects.filter(
        employee=emp, date__gte=month_start, date__lte=today
    ).order_by('-date')[:10]

    # Saldo cuti tahun ini
    leave_balances = LeaveBalance.objects.filter(
        employee=emp, year=today.year
    ).select_related('leave_type')

    # Pengajuan cuti terbaru
    leave_requests = LeaveRequest.objects.filter(
        employee=emp
    ).select_related('leave_type').order_by('-created_at')[:5]

    # Payroll detail terbaru
    payroll_details = PayrollDetail.objects.filter(
        employee=emp
    ).select_related('payroll').order_by('-payroll__period_year', '-payroll__period_month')[:6]

    # Stats kehadiran bulan ini
    att_stats = Attendance.objects.filter(
        employee=emp, date__gte=month_start, date__lte=today
    ).aggregate(
        present=Count('id', filter=Q(status__in=['PRESENT', 'LATE', 'WFH'])),
        absent=Count('id', filter=Q(status='ABSENT')),
        leave=Count('id', filter=Q(status='LEAVE')),
        late=Count('id', filter=Q(status='LATE')),
    )

    return render(request, 'hr/employee_detail.html', {
        'page_title': emp.full_name,
        'emp': emp, 'attendances': attendances,
        'leave_balances': leave_balances, 'leave_requests': leave_requests,
        'payroll_details': payroll_details, 'att_stats': att_stats,
    })


@login_required
@require_company
def employee_create(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES, company=request.company)
        if form.is_valid():
            emp = form.save(commit=False)
            emp.company = request.company
            emp.created_by = request.user
            emp.save()
            AuditLog.log(user=request.user, action=AuditLog.Action.CREATE,
                        obj=emp, company=request.company)
            messages.success(request, f'Karyawan {emp.full_name} berhasil ditambahkan.')
            return redirect('hr:employee_detail', uid=emp.uid)
    else:
        form = EmployeeForm(company=request.company)
    return render(request, 'hr/employee_form.html', {
        'page_title': 'Tambah Karyawan', 'form': form, 'action': 'create'
    })


@login_required
@require_company
def employee_edit(request, uid):
    emp = get_object_or_404(Employee, uid=uid, company=request.company)
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES, instance=emp, company=request.company)
        if form.is_valid():
            emp = form.save(commit=False)
            emp.updated_by = request.user
            emp.save()
            messages.success(request, f'{emp.full_name} berhasil diupdate.')
            return redirect('hr:employee_detail', uid=emp.uid)
    else:
        form = EmployeeForm(instance=emp, company=request.company)
    return render(request, 'hr/employee_form.html', {
        'page_title': f'Edit: {emp.full_name}', 'form': form,
        'emp': emp, 'action': 'edit'
    })


# ── ATTENDANCE ────────────────────────────────────────────────────────────────

@login_required
@require_company
def attendance_list(request):
    company = request.company
    today = timezone.now().date()
    selected_date = request.GET.get('date', today.strftime('%Y-%m-%d'))
    emp_id = request.GET.get('employee', '')

    try:
        from datetime import date as date_type
        from datetime import datetime
        view_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    except ValueError:
        view_date = today

    qs = Attendance.objects.filter(
        company=company, date=view_date
    ).select_related('employee', 'schedule').order_by('employee__first_name')

    if emp_id:
        qs = qs.filter(employee_id=emp_id)

    # Stats untuk tanggal ini
    stats = qs.aggregate(
        present=Count('id', filter=Q(status__in=['PRESENT', 'WFH'])),
        late=Count('id', filter=Q(status='LATE')),
        absent=Count('id', filter=Q(status='ABSENT')),
        leave=Count('id', filter=Q(status='LEAVE')),
    )

    employees = Employee.objects.filter(company=company, resign_date__isnull=True)

    return render(request, 'hr/attendance_list.html', {
        'page_title': 'Absensi',
        'attendances': qs, 'view_date': view_date,
        'selected_date': selected_date, 'stats': stats,
        'employees': employees, 'emp_id': emp_id,
        'today': today,
    })


@login_required
@require_company
def attendance_create(request):
    if request.method == 'POST':
        form = AttendanceForm(request.POST, company=request.company)
        if form.is_valid():
            att = form.save(commit=False)
            att.company = request.company
            att.created_by = request.user
            att.save()
            messages.success(request, 'Absensi berhasil dicatat.')
            return redirect('hr:attendance_list')
    else:
        from datetime import date
        form = AttendanceForm(company=request.company,
                              initial={'date': date.today()})
    return render(request, 'hr/attendance_form.html', {
        'page_title': 'Catat Absensi', 'form': form
    })


@login_required
@require_company
def attendance_bulk(request):
    """Catat absensi massal untuk semua karyawan dalam satu hari."""
    company = request.company
    today = timezone.now().date()

    if request.method == 'POST':
        att_date_str = request.POST.get('date', today.strftime('%Y-%m-%d'))
        from datetime import datetime
        att_date = datetime.strptime(att_date_str, '%Y-%m-%d').date()

        employees = Employee.objects.filter(company=company, resign_date__isnull=True)
        created = 0
        for emp in employees:
            status = request.POST.get(f'status_{emp.pk}', 'PRESENT')
            check_in = request.POST.get(f'checkin_{emp.pk}', '') or None
            check_out = request.POST.get(f'checkout_{emp.pk}', '') or None
            notes = request.POST.get(f'notes_{emp.pk}', '')

            att, created_new = Attendance.objects.update_or_create(
                company=company, employee=emp, date=att_date,
                defaults={
                    'status': status,
                    'check_in': check_in,
                    'check_out': check_out,
                    'notes': notes,
                    'created_by': request.user,
                }
            )
            if created_new:
                created += 1

        messages.success(request, f'Absensi {att_date} berhasil disimpan.')
        return redirect('hr:attendance_list')

    employees = Employee.objects.filter(
        company=company, resign_date__isnull=True
    ).select_related('department').order_by('department__name', 'first_name')

    # Cek absensi hari ini yang sudah ada
    existing = {
        a.employee_id: a
        for a in Attendance.objects.filter(company=company, date=today)
    }

    return render(request, 'hr/attendance_bulk.html', {
        'page_title': 'Absensi Massal',
        'employees': employees, 'today': today,
        'existing': existing,
        'statuses': Attendance.Status.choices,
    })


# ── LEAVE ─────────────────────────────────────────────────────────────────────

@login_required
@require_company
def leave_list(request):
    status = request.GET.get('status', '')
    qs = LeaveRequest.objects.filter(
        company=request.company
    ).select_related('employee', 'leave_type').order_by('-created_at')
    if status:
        qs = qs.filter(status=status)
    page = Paginator(qs, 20).get_page(request.GET.get('page', 1))
    return render(request, 'hr/leave_list.html', {
        'page_title': 'Pengajuan Cuti',
        'leaves': page, 'selected_status': status,
        'statuses': LeaveRequest.Status.choices,
        'counts': {s.value: LeaveRequest.objects.filter(
            company=request.company, status=s).count()
            for s in LeaveRequest.Status},
    })


@login_required
@require_company
def leave_create(request):
    if request.method == 'POST':
        form = LeaveRequestForm(request.POST, request.FILES, company=request.company)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.company = request.company
            leave.created_by = request.user
            leave.save()
            messages.success(request, f'Pengajuan cuti berhasil dibuat.')
            return redirect('hr:leave_detail', uid=leave.uid)
    else:
        form = LeaveRequestForm(company=request.company)
    return render(request, 'hr/leave_form.html', {
        'page_title': 'Ajukan Cuti', 'form': form
    })


@login_required
@require_company
def leave_detail(request, uid):
    leave = get_object_or_404(LeaveRequest, uid=uid, company=request.company)
    # Cek saldo cuti
    today = timezone.now().date()
    try:
        balance = LeaveBalance.objects.get(
            employee=leave.employee,
            leave_type=leave.leave_type,
            year=leave.start_date.year if leave.start_date else today.year
        )
    except LeaveBalance.DoesNotExist:
        balance = None

    return render(request, 'hr/leave_detail.html', {
        'page_title': f'Cuti — {leave.employee.full_name}',
        'leave': leave, 'balance': balance,
    })


@login_required
@require_company
@require_POST
def leave_approve(request, uid):
    leave = get_object_or_404(LeaveRequest, uid=uid, company=request.company)
    if leave.status != LeaveRequest.Status.PENDING:
        messages.error(request, 'Cuti tidak berstatus Pending.')
        return redirect('hr:leave_detail', uid=leave.uid)
    notes = request.POST.get('notes', '')
    leave.approve(request.user, notes)
    messages.success(request, f'Cuti {leave.employee.full_name} disetujui.')
    return redirect('hr:leave_detail', uid=leave.uid)


@login_required
@require_company
@require_POST
def leave_reject(request, uid):
    leave = get_object_or_404(LeaveRequest, uid=uid, company=request.company)
    reason = request.POST.get('reason', '').strip()
    if not reason:
        messages.error(request, 'Alasan penolakan wajib diisi.')
        return redirect('hr:leave_detail', uid=leave.uid)
    leave.reject(request.user, reason)
    messages.success(request, 'Cuti ditolak.')
    return redirect('hr:leave_detail', uid=leave.uid)


@login_required
@require_company
@require_POST
def leave_submit(request, uid):
    leave = get_object_or_404(LeaveRequest, uid=uid, company=request.company)
    if leave.status != LeaveRequest.Status.DRAFT:
        messages.error(request, 'Hanya draft yang bisa disubmit.')
        return redirect('hr:leave_detail', uid=leave.uid)
    leave.status = LeaveRequest.Status.PENDING
    leave.save(update_fields=['status'])
    messages.success(request, 'Cuti disubmit untuk approval.')
    return redirect('hr:leave_detail', uid=leave.uid)


# ── PAYROLL ───────────────────────────────────────────────────────────────────

@login_required
@require_company
def payroll_list(request):
    qs = Payroll.objects.filter(company=request.company).order_by('-period_year', '-period_month')
    page = Paginator(qs, 20).get_page(request.GET.get('page', 1))
    return render(request, 'hr/payroll_list.html', {
        'page_title': 'Payroll', 'payrolls': page,
    })


@login_required
@require_company
def payroll_create(request):
    if request.method == 'POST':
        form = PayrollForm(request.POST, company=request.company)
        if form.is_valid():
            payroll = form.save(commit=False)
            payroll.company = request.company
            payroll.created_by = request.user
            payroll.save()
            messages.success(request, f'Payroll {payroll.name} berhasil dibuat.')
            return redirect('hr:payroll_detail', uid=payroll.uid)
    else:
        today = timezone.now()
        form = PayrollForm(company=request.company,
                           initial={'period_month': today.month, 'period_year': today.year,
                                    'name': f'Gaji {today.strftime("%B %Y")}'})
    return render(request, 'hr/payroll_form.html', {
        'page_title': 'Buat Payroll', 'form': form
    })


@login_required
@require_company
def payroll_detail(request, uid):
    payroll = get_object_or_404(Payroll, uid=uid, company=request.company)
    details = payroll.details.select_related(
        'employee', 'employee__department', 'employee__position'
    ).prefetch_related('items__component').order_by('employee__first_name')
    return render(request, 'hr/payroll_detail.html', {
        'page_title': payroll.name, 'payroll': payroll, 'details': details,
    })


@login_required
@require_company
@require_POST
def payroll_calculate(request, uid):
    payroll = get_object_or_404(Payroll, uid=uid, company=request.company)
    try:
        payroll.calculate(user=request.user)
        messages.success(request, f'Payroll {payroll.name} berhasil dihitung — {payroll.employee_count} karyawan.')
    except ValueError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
    return redirect('hr:payroll_detail', uid=payroll.uid)


@login_required
@require_company
@require_POST
def payroll_approve(request, uid):
    payroll = get_object_or_404(Payroll, uid=uid, company=request.company)
    try:
        payroll.approve(request.user)
        messages.success(request, f'Payroll {payroll.name} disetujui.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('hr:payroll_detail', uid=payroll.uid)


@login_required
@require_company
def payroll_detail_employee(request, payroll_uid, emp_uid):
    """Detail komponen gaji satu karyawan dalam satu payroll."""
    payroll = get_object_or_404(Payroll, uid=payroll_uid, company=request.company)
    emp = get_object_or_404(Employee, uid=emp_uid, company=request.company)
    detail = get_object_or_404(PayrollDetail, payroll=payroll, employee=emp)
    items = detail.items.select_related('component').order_by(
        'component__component_type', 'component__order'
    )
    return render(request, 'hr/payroll_detail_employee.html', {
        'page_title': f'Slip Gaji — {emp.full_name}',
        'payroll': payroll, 'emp': emp, 'detail': detail, 'items': items,
    })


# ── PAYSLIP PDF ───────────────────────────────────────────────────────────────

@login_required
@require_company
def payslip_pdf(request, payroll_uid, emp_uid):
    """Generate slip gaji PDF untuk satu karyawan."""
    from core.exports import PDFExporter
    from reportlab.platypus import Paragraph, Spacer, HRFlowable, Table, TableStyle
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import cm

    payroll = get_object_or_404(Payroll, uid=payroll_uid, company=request.company)
    emp = get_object_or_404(Employee, uid=emp_uid, company=request.company)
    detail = get_object_or_404(PayrollDetail, payroll=payroll, employee=emp)
    items = detail.items.select_related('component').order_by(
        'component__component_type', 'component__order'
    )
    company = request.company

    pdf = PDFExporter(f"Slip Gaji — {payroll.name}", company)

    # Header
    pdf.build_header()

    # Info karyawan & periode
    pdf.add_info_grid([
        ("Nama Karyawan", emp.full_name),
        ("NIK Karyawan", emp.employee_id),
        ("Jabatan", emp.position.name if emp.position else '—'),
        ("Departemen", emp.department.name if emp.department else '—'),
        ("Periode", f"{payroll.period_month:02d}/{payroll.period_year}"),
        ("Status", emp.get_employment_status_display()),
        ("Bank", emp.bank_name or '—'),
        ("No. Rekening", emp.bank_account or '—'),
    ])

    # Info kehadiran
    pdf.add_table(
        ['Keterangan', 'Hari'],
        [
            ['Hari Hadir', str(detail.present_days)],
            ['Hari Cuti', str(detail.leave_days)],
            ['Hari Tidak Hadir', str(detail.absent_days)],
            ['Total Hari Kerja', str(detail.working_days)],
            ['Lembur (menit)', str(detail.overtime_minutes)],
        ],
        [12, 6],
        "Kehadiran"
    )

    # Pendapatan
    earnings = [(i.component.name, f"Rp {i.amount:,.0f}")
                for i in items if i.component.component_type == 'EARNING']
    if earnings:
        pdf.add_table(
            ['Komponen Pendapatan', 'Jumlah'],
            [['Gaji Pokok', f"Rp {detail.basic_salary:,.0f}"]] + earnings,
            [12, 6],
            "Pendapatan"
        )

    # Potongan
    deductions = [(i.component.name, f"Rp {i.amount:,.0f}")
                  for i in items if i.component.component_type == 'DEDUCTION']
    if deductions:
        pdf.add_table(['Komponen Potongan', 'Jumlah'], deductions, [12, 6], "Potongan")

    # Summary total
    pdf.add_summary([
        ("Gaji Pokok", f"Rp {detail.basic_salary:,.0f}"),
        ("Total Tunjangan", f"Rp {detail.total_earnings:,.0f}"),
        ("Gaji Kotor", f"Rp {detail.gross_salary:,.0f}"),
        ("Total Potongan", f"Rp {detail.total_deductions:,.0f}"),
        ("GAJI BERSIH (Take Home Pay)", f"Rp {detail.net_salary:,.0f}"),
    ])

    return pdf.response(
        f"SlipGaji_{emp.employee_id}_{payroll.period_year}{payroll.period_month:02d}.pdf"
    )


@login_required
@require_company
def payroll_export_excel(request, uid):
    """Export payroll ke Excel — semua karyawan."""
    from core.exports import ExcelExporter
    payroll = get_object_or_404(Payroll, uid=uid, company=request.company)
    details = payroll.details.select_related('employee', 'employee__department', 'employee__position')

    exp = ExcelExporter(f"Payroll {payroll.name}", request.company.name)

    # Sheet 1: Summary
    headers = ['NIK', 'Nama', 'Dept', 'Jabatan', 'Gaji Pokok',
               'Tunjangan', 'Gaji Kotor', 'Potongan', 'Gaji Bersih',
               'Hadir', 'Cuti', 'Absen', 'Bank', 'No. Rekening']
    rows = []
    for d in details:
        rows.append([
            d.employee.employee_id, d.employee.full_name,
            d.employee.department.name if d.employee.department else '',
            d.employee.position.name if d.employee.position else '',
            float(d.basic_salary), float(d.total_earnings),
            float(d.gross_salary), float(d.total_deductions), float(d.net_salary),
            d.present_days, d.leave_days, d.absent_days,
            d.employee.bank_name, d.employee.bank_account,
        ])
    exp.add_sheet("Payroll Summary", headers, rows,
                  [12, 22, 16, 18, 14, 12, 14, 12, 14, 8, 8, 8, 14, 16])

    # Sheet 2: Transfer (untuk bank)
    headers2 = ['No. Rekening', 'Nama Penerima', 'Bank', 'Jumlah Transfer', 'Keterangan']
    rows2 = []
    for d in details:
        rows2.append([
            d.employee.bank_account or '',
            d.employee.bank_account_name or d.employee.full_name,
            d.employee.bank_name or '',
            float(d.net_salary),
            f"Gaji {payroll.period_month:02d}/{payroll.period_year} — {d.employee.employee_id}",
        ])
    exp.add_sheet("Data Transfer Bank", headers2, rows2,
                  [18, 24, 14, 14, 30])

    return exp.response(
        f"Payroll_{request.company.code}_{payroll.period_year}{payroll.period_month:02d}.xlsx"
    )
