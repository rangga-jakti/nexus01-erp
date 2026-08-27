"""
hr/models.py

Modul HR Nexus-01:
Employee → Contract → Attendance → Leave → Payroll → PayrollItem → PaySlip

Semua terintegrasi dengan:
- Organization (Company, Branch, Department)
- Core (ApprovalRequest, AuditLog, Notification)
- Finance (Expense untuk payroll cost)
- Accounts (User)
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from core.models import CompanyBoundModel, NexusBaseModel
import uuid


# ─────────────────────────────────────────────────────────────────────────────
# EMPLOYEE
# ─────────────────────────────────────────────────────────────────────────────

class JobPosition(CompanyBoundModel):
    """Jabatan/posisi pekerjaan."""
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=200)
    department = models.ForeignKey(
        'organization.Department', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='positions'
    )
    description = models.TextField(blank=True)
    basic_salary_min = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    basic_salary_max = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        unique_together = ['company', 'code']
        ordering = ['name']

    def __str__(self):
        return f"{self.code} — {self.name}"


class Employee(CompanyBoundModel):
    """
    Data master karyawan.
    Terhubung ke User account (opsional — tidak semua karyawan punya akun sistem).
    """

    class Gender(models.TextChoices):
        MALE = 'M', 'Laki-laki'
        FEMALE = 'F', 'Perempuan'

    class MaritalStatus(models.TextChoices):
        SINGLE = 'SINGLE', 'Belum Menikah'
        MARRIED = 'MARRIED', 'Menikah'
        DIVORCED = 'DIVORCED', 'Cerai'
        WIDOWED = 'WIDOWED', 'Janda/Duda'

    class EmploymentStatus(models.TextChoices):
        PERMANENT = 'PERMANENT', 'Karyawan Tetap'
        CONTRACT = 'CONTRACT', 'Kontrak'
        INTERNSHIP = 'INTERNSHIP', 'Magang'
        PART_TIME = 'PART_TIME', 'Paruh Waktu'
        PROBATION = 'PROBATION', 'Percobaan'

    class TaxStatus(models.TextChoices):
        TK0 = 'TK0', 'TK/0 - Tidak Kawin, 0 tanggungan'
        TK1 = 'TK1', 'TK/1 - Tidak Kawin, 1 tanggungan'
        TK2 = 'TK2', 'TK/2 - Tidak Kawin, 2 tanggungan'
        TK3 = 'TK3', 'TK/3 - Tidak Kawin, 3 tanggungan'
        K0  = 'K0',  'K/0 - Kawin, 0 tanggungan'
        K1  = 'K1',  'K/1 - Kawin, 1 tanggungan'
        K2  = 'K2',  'K/2 - Kawin, 2 tanggungan'
        K3  = 'K3',  'K/3 - Kawin, 3 tanggungan'

    # Link ke user account (opsional)
    user = models.OneToOneField(
        'accounts.User', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='employee_profile'
    )

    # Identifikasi
    employee_id = models.CharField(max_length=20, help_text="NIK Karyawan, e.g. EMP-001")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    gender = models.CharField(max_length=1, choices=Gender.choices)
    birth_date = models.DateField(null=True, blank=True)
    birth_place = models.CharField(max_length=100, blank=True)
    nationality = models.CharField(max_length=50, default='Indonesia')
    religion = models.CharField(max_length=50, blank=True)
    marital_status = models.CharField(
        max_length=10, choices=MaritalStatus.choices, default=MaritalStatus.SINGLE
    )
    dependents = models.PositiveSmallIntegerField(default=0, help_text="Jumlah tanggungan")

    # Dokumen
    nik = models.CharField(max_length=16, blank=True, help_text="NIK KTP")
    npwp = models.CharField(max_length=20, blank=True, help_text="NPWP")
    bpjs_kes = models.CharField(max_length=30, blank=True, help_text="No. BPJS Kesehatan")
    bpjs_tk = models.CharField(max_length=30, blank=True, help_text="No. BPJS Ketenagakerjaan")
    tax_status = models.CharField(
        max_length=5, choices=TaxStatus.choices, default=TaxStatus.TK0
    )

    # Kontak
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    emergency_contact = models.CharField(max_length=100, blank=True)
    emergency_phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)

    # Posisi & organisasi
    branch = models.ForeignKey(
        'organization.Branch', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='employees'
    )
    department = models.ForeignKey(
        'organization.Department', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='employees'
    )
    position = models.ForeignKey(
        JobPosition, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='employees'
    )
    direct_manager = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='subordinates'
    )

    # Employment
    employment_status = models.CharField(
        max_length=20, choices=EmploymentStatus.choices,
        default=EmploymentStatus.PERMANENT
    )
    join_date = models.DateField()
    end_date = models.DateField(null=True, blank=True, help_text="Untuk karyawan kontrak")
    resign_date = models.DateField(null=True, blank=True)

    # Rekening
    bank_name = models.CharField(max_length=100, blank=True)
    bank_account = models.CharField(max_length=30, blank=True)
    bank_account_name = models.CharField(max_length=100, blank=True)

    # Gaji
    basic_salary = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # Photo
    photo = models.ImageField(upload_to='employee_photos/', null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['company', 'employee_id']
        ordering = ['first_name', 'last_name']

    def __str__(self):
        return f"{self.employee_id} — {self.full_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def age(self):
        if self.birth_date:
            today = timezone.now().date()
            return today.year - self.birth_date.year - (
                (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
            )
        return None

    @property
    def years_of_service(self):
        today = timezone.now().date()
        delta = today - self.join_date
        return round(delta.days / 365.25, 1)

    @property
    def is_active(self):
        return self.resign_date is None


# ─────────────────────────────────────────────────────────────────────────────
# ATTENDANCE
# ─────────────────────────────────────────────────────────────────────────────

class WorkSchedule(CompanyBoundModel):
    """Jadwal kerja — shift."""
    name = models.CharField(max_length=100, help_text="e.g. Shift Pagi, WFH, Normal")
    code = models.CharField(max_length=20)
    work_start = models.TimeField()
    work_end = models.TimeField()
    break_start = models.TimeField(null=True, blank=True)
    break_end = models.TimeField(null=True, blank=True)
    late_tolerance_minutes = models.PositiveSmallIntegerField(
        default=15, help_text="Toleransi keterlambatan dalam menit"
    )
    work_days = models.CharField(
        max_length=20, default='1,2,3,4,5',
        help_text="Hari kerja: 1=Senin, 7=Minggu (comma separated)"
    )

    class Meta:
        unique_together = ['company', 'code']

    def __str__(self):
        return f"{self.name} ({self.work_start:%H:%M}–{self.work_end:%H:%M})"

    @property
    def work_hours(self):
        from datetime import datetime, date
        start = datetime.combine(date.today(), self.work_start)
        end = datetime.combine(date.today(), self.work_end)
        diff = (end - start).seconds / 3600
        if self.break_start and self.break_end:
            bs = datetime.combine(date.today(), self.break_start)
            be = datetime.combine(date.today(), self.break_end)
            diff -= (be - bs).seconds / 3600
        return round(diff, 1)


class Attendance(CompanyBoundModel):
    """
    Record absensi harian per karyawan.
    Satu record = satu hari kerja.
    """

    class Status(models.TextChoices):
        PRESENT = 'PRESENT', 'Hadir'
        ABSENT = 'ABSENT', 'Tidak Hadir'
        LATE = 'LATE', 'Terlambat'
        HALF_DAY = 'HALF_DAY', 'Setengah Hari'
        LEAVE = 'LEAVE', 'Cuti'
        SICK = 'SICK', 'Sakit'
        HOLIDAY = 'HOLIDAY', 'Hari Libur'
        WFH = 'WFH', 'Work From Home'

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField(db_index=True)
    schedule = models.ForeignKey(
        WorkSchedule, null=True, blank=True, on_delete=models.SET_NULL
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PRESENT, db_index=True
    )

    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    check_in_location = models.CharField(max_length=200, blank=True)
    check_out_location = models.CharField(max_length=200, blank=True)

    late_minutes = models.PositiveSmallIntegerField(default=0)
    early_leave_minutes = models.PositiveSmallIntegerField(default=0)
    overtime_minutes = models.PositiveSmallIntegerField(default=0)

    notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        'accounts.User', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='approved_attendances'
    )

    class Meta:
        unique_together = ['employee', 'date']
        ordering = ['-date', 'employee__first_name']

    def __str__(self):
        return f"{self.employee.full_name} — {self.date} [{self.get_status_display()}]"

    def save(self, *args, **kwargs):
        """Auto-calculate late minutes dan overtime."""
        if self.check_in and self.schedule:
            from datetime import datetime, date
            scheduled = datetime.combine(date.today(), self.schedule.work_start)
            actual = datetime.combine(date.today(), self.check_in)
            diff = (actual - scheduled).seconds // 60
            tolerance = self.schedule.late_tolerance_minutes
            if diff > tolerance and actual > scheduled:
                self.late_minutes = diff - tolerance
                if self.status == self.Status.PRESENT:
                    self.status = self.Status.LATE

        if self.check_out and self.schedule:
            from datetime import datetime, date
            scheduled_end = datetime.combine(date.today(), self.schedule.work_end)
            actual_out = datetime.combine(date.today(), self.check_out)
            if actual_out > scheduled_end:
                self.overtime_minutes = (actual_out - scheduled_end).seconds // 60

        super().save(*args, **kwargs)

    @property
    def work_duration_hours(self):
        if self.check_in and self.check_out:
            from datetime import datetime, date
            ci = datetime.combine(date.today(), self.check_in)
            co = datetime.combine(date.today(), self.check_out)
            return round((co - ci).seconds / 3600, 2)
        return 0


# ─────────────────────────────────────────────────────────────────────────────
# LEAVE (CUTI)
# ─────────────────────────────────────────────────────────────────────────────

class LeaveType(CompanyBoundModel):
    """Jenis cuti — tahunan, sakit, melahirkan, dll."""
    code = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    max_days_per_year = models.PositiveSmallIntegerField(
        default=12, help_text="Maksimal hari cuti per tahun. 0 = tidak terbatas"
    )
    is_paid = models.BooleanField(default=True, help_text="Cuti berbayar")
    requires_approval = models.BooleanField(default=True)
    carry_forward = models.BooleanField(
        default=False, help_text="Saldo cuti bisa dibawa ke tahun berikutnya"
    )
    gender_specific = models.CharField(
        max_length=1, choices=[('', 'Semua'), ('M', 'Pria'), ('F', 'Wanita')],
        blank=True, default='', help_text="Kosong = untuk semua gender"
    )

    class Meta:
        unique_together = ['company', 'code']

    def __str__(self):
        return f"{self.code} — {self.name}"


class LeaveBalance(CompanyBoundModel):
    """Saldo cuti karyawan per tahun per jenis cuti."""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_balances')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    year = models.PositiveSmallIntegerField()
    total_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    used_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    carry_forward_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)

    class Meta:
        unique_together = ['employee', 'leave_type', 'year']

    def __str__(self):
        return f"{self.employee.full_name} — {self.leave_type.name} {self.year}"

    @property
    def remaining_days(self):
        return self.total_days + self.carry_forward_days - self.used_days


class LeaveRequest(CompanyBoundModel):
    """Pengajuan cuti karyawan."""

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PENDING = 'PENDING', 'Menunggu Approval'
        APPROVED = 'APPROVED', 'Disetujui'
        REJECTED = 'REJECTED', 'Ditolak'
        CANCELLED = 'CANCELLED', 'Dibatalkan'

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    start_date = models.DateField()
    end_date = models.DateField()
    total_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    reason = models.TextField()
    attachment = models.FileField(upload_to='leave_attachments/', null=True, blank=True)
    approved_by = models.ForeignKey(
        'accounts.User', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='approved_leaves'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employee.full_name} — {self.leave_type.name} ({self.start_date} s/d {self.end_date})"

    def save(self, *args, **kwargs):
        if self.start_date and self.end_date:
            # Hitung hari kerja (exclude weekend)
            from datetime import timedelta
            delta = self.end_date - self.start_date
            working_days = 0
            for i in range(delta.days + 1):
                day = self.start_date + timedelta(days=i)
                if day.weekday() < 5:  # Senin-Jumat
                    working_days += 1
            self.total_days = working_days
        super().save(*args, **kwargs)

    def approve(self, approver, notes=''):
        from django.utils import timezone as tz
        self.status = self.Status.APPROVED
        self.approved_by = approver
        self.approved_at = tz.now()
        self.notes = notes
        self.save()

        # Update leave balance
        try:
            balance = LeaveBalance.objects.get(
                employee=self.employee,
                leave_type=self.leave_type,
                year=self.start_date.year,
            )
            balance.used_days += self.total_days
            balance.save(update_fields=['used_days'])
        except LeaveBalance.DoesNotExist:
            pass

        # Buat attendance record untuk hari cuti
        from datetime import timedelta
        delta = self.end_date - self.start_date
        for i in range(delta.days + 1):
            day = self.start_date + timedelta(days=i)
            if day.weekday() < 5:
                Attendance.objects.get_or_create(
                    company=self.company,
                    employee=self.employee,
                    date=day,
                    defaults={
                        'status': Attendance.Status.LEAVE,
                        'notes': f'Cuti: {self.leave_type.name}',
                    }
                )

        from core.models import AuditLog
        AuditLog.log(
            user=approver, action=AuditLog.Action.APPROVE,
            obj=self, company=self.company,
            message=f'Cuti {self.employee.full_name} disetujui'
        )

    def reject(self, approver, reason):
        self.status = self.Status.REJECTED
        self.approved_by = approver
        self.rejection_reason = reason
        self.save()


# ─────────────────────────────────────────────────────────────────────────────
# PAYROLL
# ─────────────────────────────────────────────────────────────────────────────

class PayrollComponent(CompanyBoundModel):
    """
    Komponen gaji — bisa berupa tunjangan (penambah) atau potongan (pengurang).
    Contoh tunjangan: Tunjangan Makan, Transport, Jabatan, Lembur
    Contoh potongan: BPJS Kes (4%), BPJS TK (2%), PPh 21, Kasbon
    """

    class ComponentType(models.TextChoices):
        EARNING = 'EARNING', 'Pendapatan (Tunjangan)'
        DEDUCTION = 'DEDUCTION', 'Potongan'

    class CalculationType(models.TextChoices):
        FIXED = 'FIXED', 'Nominal Tetap'
        PERCENTAGE_BASIC = 'PERCENTAGE_BASIC', '% dari Gaji Pokok'
        PERCENTAGE_GROSS = 'PERCENTAGE_GROSS', '% dari Gaji Kotor'
        FORMULA = 'FORMULA', 'Formula Kustom'

    code = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    component_type = models.CharField(max_length=10, choices=ComponentType.choices)
    calculation_type = models.CharField(
        max_length=20, choices=CalculationType.choices, default=CalculationType.FIXED
    )
    default_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        help_text="Nominal default. Untuk % masukkan nilai persen (e.g. 4 untuk 4%)"
    )
    is_taxable = models.BooleanField(default=True, help_text="Kena PPh 21")
    is_mandatory = models.BooleanField(
        default=False, help_text="Wajib ada di semua payroll"
    )
    order = models.PositiveSmallIntegerField(default=0, help_text="Urutan tampil di slip gaji")

    class Meta:
        unique_together = ['company', 'code']
        ordering = ['component_type', 'order', 'name']

    def __str__(self):
        return f"{self.code} — {self.name} ({self.get_component_type_display()})"


class Payroll(CompanyBoundModel):
    """
    Header payroll bulanan.
    Satu payroll = satu periode (bulan/tahun) untuk semua karyawan atau batch tertentu.
    """

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        CALCULATED = 'CALCULATED', 'Sudah Dihitung'
        APPROVED = 'APPROVED', 'Disetujui'
        PAID = 'PAID', 'Sudah Dibayar'
        CANCELLED = 'CANCELLED', 'Dibatalkan'

    period_month = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    period_year = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=200, help_text="e.g. 'Gaji Agustus 2026'")
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    branch = models.ForeignKey(
        'organization.Branch', null=True, blank=True, on_delete=models.SET_NULL
    )
    payment_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        'accounts.User', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='approved_payrolls'
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    # Summary totals (di-cache setelah calculate)
    total_basic_salary = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_earnings = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_net_salary = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    employee_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ['company', 'period_month', 'period_year', 'branch']
        ordering = ['-period_year', '-period_month']

    def __str__(self):
        return f"{self.name} [{self.get_status_display()}]"

    def calculate(self, user=None):
        """
        Hitung gaji semua karyawan aktif untuk periode ini.
        Buat PayrollDetail per karyawan dan PayrollItem per komponen.
        """
        from django.db.models import Count, Q
        from datetime import date

        if self.status not in [self.Status.DRAFT, self.Status.CALCULATED]:
            raise ValueError("Hanya payroll berstatus Draft yang bisa dihitung ulang.")

        # Ambil karyawan aktif
        employees = Employee.objects.filter(
            company=self.company,
            is_active=True,
            resign_date__isnull=True,
            join_date__lte=date(self.period_year, self.period_month, 28),
        )
        if self.branch:
            employees = employees.filter(branch=self.branch)

        # Hapus detail lama
        self.details.all().delete()

        period_start = date(self.period_year, self.period_month, 1)
        import calendar
        period_end = date(
            self.period_year, self.period_month,
            calendar.monthrange(self.period_year, self.period_month)[1]
        )

        total_basic = total_earn = total_ded = total_net = 0

        for emp in employees:
            # Hitung kehadiran periode ini
            attendances = Attendance.objects.filter(
                employee=emp,
                date__range=[period_start, period_end]
            )
            present_days = attendances.filter(
                status__in=['PRESENT', 'LATE', 'WFH']
            ).count()
            leave_days = attendances.filter(status='LEAVE').count()
            absent_days = attendances.filter(status='ABSENT').count()
            overtime_minutes = sum(a.overtime_minutes for a in attendances)
            late_minutes = sum(a.late_minutes for a in attendances)

            # Buat PayrollDetail
            detail = PayrollDetail.objects.create(
                company=self.company,
                payroll=self,
                employee=emp,
                basic_salary=emp.basic_salary,
                present_days=present_days,
                leave_days=leave_days,
                absent_days=absent_days,
                overtime_minutes=overtime_minutes,
                late_minutes=late_minutes,
                working_days=present_days + leave_days,
            )

            # Hitung komponen wajib
            mandatory_components = PayrollComponent.objects.filter(
                company=self.company, is_mandatory=True, is_active=True
            )
            for comp in mandatory_components:
                detail.add_component(comp)

            detail.calculate_totals()
            total_basic += detail.basic_salary
            total_earn += detail.total_earnings
            total_ded += detail.total_deductions
            total_net += detail.net_salary

        # Update summary
        self.total_basic_salary = total_basic
        self.total_earnings = total_earn
        self.total_deductions = total_ded
        self.total_net_salary = total_net
        self.employee_count = employees.count()
        self.status = self.Status.CALCULATED
        self.save()

        from core.models import AuditLog
        AuditLog.log(
            user=user, action=AuditLog.Action.UPDATE,
            obj=self, company=self.company,
            message=f'Payroll {self.name} dihitung: {self.employee_count} karyawan'
        )

    def approve(self, user):
        from django.utils import timezone as tz
        if self.status != self.Status.CALCULATED:
            raise ValueError("Payroll harus dihitung dulu sebelum disetujui.")
        self.status = self.Status.APPROVED
        self.approved_by = user
        self.approved_at = tz.now()
        self.save()

        from core.models import AuditLog
        AuditLog.log(
            user=user, action=AuditLog.Action.APPROVE,
            obj=self, company=self.company,
            message=f'Payroll {self.name} disetujui'
        )


class PayrollDetail(CompanyBoundModel):
    """Detail payroll per karyawan — satu baris = satu karyawan dalam satu payroll."""

    payroll = models.ForeignKey(Payroll, on_delete=models.CASCADE, related_name='details')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payroll_details')

    basic_salary = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    present_days = models.PositiveSmallIntegerField(default=0)
    leave_days = models.PositiveSmallIntegerField(default=0)
    absent_days = models.PositiveSmallIntegerField(default=0)
    working_days = models.PositiveSmallIntegerField(default=0)
    overtime_minutes = models.PositiveIntegerField(default=0)
    late_minutes = models.PositiveIntegerField(default=0)

    # Summary (dihitung dari items)
    total_earnings = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    gross_salary = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    pph21 = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['payroll', 'employee']
        ordering = ['employee__first_name']

    def __str__(self):
        return f"{self.payroll.name} — {self.employee.full_name}"

    def add_component(self, component, custom_amount=None):
        """Tambah komponen gaji ke detail ini."""
        if custom_amount is not None:
            amount = custom_amount
        elif component.calculation_type == PayrollComponent.CalculationType.FIXED:
            amount = component.default_amount
        elif component.calculation_type == PayrollComponent.CalculationType.PERCENTAGE_BASIC:
            amount = self.basic_salary * component.default_amount / 100
        elif component.calculation_type == PayrollComponent.CalculationType.PERCENTAGE_GROSS:
            amount = self.gross_salary * component.default_amount / 100
        else:
            amount = component.default_amount

        PayrollItem.objects.update_or_create(
            payroll_detail=self,
            component=component,
            defaults={'amount': amount}
        )

    def calculate_totals(self):
        """Recalculate total dari semua items."""
        items = self.items.select_related('component')
        earnings = sum(
            i.amount for i in items
            if i.component.component_type == PayrollComponent.ComponentType.EARNING
        )
        deductions = sum(
            i.amount for i in items
            if i.component.component_type == PayrollComponent.ComponentType.DEDUCTION
        )
        gross = self.basic_salary + earnings
        net = gross - deductions

        self.total_earnings = earnings
        self.total_deductions = deductions
        self.gross_salary = gross
        self.net_salary = net
        self.save(update_fields=[
            'total_earnings', 'total_deductions',
            'gross_salary', 'net_salary'
        ])


class PayrollItem(models.Model):
    """Line item komponen gaji dalam satu PayrollDetail."""
    payroll_detail = models.ForeignKey(
        PayrollDetail, on_delete=models.CASCADE, related_name='items'
    )
    component = models.ForeignKey(PayrollComponent, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ['payroll_detail', 'component']
        ordering = ['component__component_type', 'component__order']

    def __str__(self):
        return f"{self.component.name}: {self.amount:,.0f}"
