from django.contrib import admin
from .models import (
    JobPosition, Employee, WorkSchedule, Attendance,
    LeaveType, LeaveBalance, LeaveRequest,
    PayrollComponent, Payroll, PayrollDetail, PayrollItem
)


@admin.register(JobPosition)
class JobPositionAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'department', 'company', 'is_active']
    list_filter = ['company', 'department']
    search_fields = ['code', 'name']


class PayrollItemInline(admin.TabularInline):
    model = PayrollItem
    extra = 0
    fields = ['component', 'amount', 'notes']


class PayrollDetailInline(admin.TabularInline):
    model = PayrollDetail
    extra = 0
    fields = ['employee', 'basic_salary', 'working_days', 'gross_salary', 'net_salary']
    readonly_fields = ['gross_salary', 'net_salary']


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'full_name', 'department', 'position',
                    'employment_status', 'join_date', 'is_active']
    list_filter = ['company', 'employment_status', 'department', 'gender']
    search_fields = ['employee_id', 'first_name', 'last_name', 'nik']
    readonly_fields = ['uid', 'created_at', 'updated_at']
    fieldsets = (
        ('Identitas', {'fields': (
            'employee_id', 'first_name', 'last_name', 'gender',
            'birth_date', 'birth_place', 'nationality', 'religion',
            'marital_status', 'dependents', 'photo'
        )}),
        ('Dokumen', {'fields': ('nik', 'npwp', 'bpjs_kes', 'bpjs_tk', 'tax_status')}),
        ('Kontak', {'fields': ('email', 'phone', 'address', 'city',
                                'emergency_contact', 'emergency_phone')}),
        ('Posisi', {'fields': ('company', 'branch', 'department', 'position',
                                'direct_manager', 'employment_status')}),
        ('Employment', {'fields': ('join_date', 'end_date', 'resign_date')}),
        ('Rekening & Gaji', {'fields': ('bank_name', 'bank_account',
                                         'bank_account_name', 'basic_salary')}),
        ('Lainnya', {'fields': ('user', 'notes', 'uid', 'created_at', 'updated_at')}),
    )


@admin.register(WorkSchedule)
class WorkScheduleAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'work_start', 'work_end', 'work_hours', 'company']
    list_filter = ['company']


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['date', 'employee', 'status', 'check_in', 'check_out',
                    'late_minutes', 'overtime_minutes']
    list_filter = ['status', 'company', 'date']
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__employee_id']
    date_hierarchy = 'date'


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'max_days_per_year', 'is_paid', 'requires_approval']
    list_filter = ['company']


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'year', 'total_days', 'used_days', 'remaining_days']
    list_filter = ['company', 'year', 'leave_type']
    search_fields = ['employee__first_name', 'employee__last_name']


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'status', 'start_date', 'end_date', 'total_days']
    list_filter = ['status', 'company', 'leave_type']
    search_fields = ['employee__first_name', 'employee__last_name']
    readonly_fields = ['total_days', 'uid', 'created_at']


@admin.register(PayrollComponent)
class PayrollComponentAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'component_type', 'calculation_type',
                    'default_amount', 'is_mandatory', 'is_taxable']
    list_filter = ['company', 'component_type', 'is_mandatory']
    search_fields = ['code', 'name']


@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ['name', 'period_month', 'period_year', 'status',
                    'employee_count', 'total_net_salary', 'payment_date']
    list_filter = ['status', 'company', 'period_year']
    readonly_fields = ['total_basic_salary', 'total_earnings', 'total_deductions',
                       'total_net_salary', 'employee_count', 'uid', 'created_at']
    inlines = [PayrollDetailInline]


@admin.register(PayrollDetail)
class PayrollDetailAdmin(admin.ModelAdmin):
    list_display = ['employee', 'payroll', 'basic_salary', 'gross_salary',
                    'total_deductions', 'net_salary']
    list_filter = ['payroll__period_year', 'company']
    search_fields = ['employee__first_name', 'employee__last_name']
    readonly_fields = ['gross_salary', 'net_salary', 'total_earnings', 'total_deductions']
    inlines = [PayrollItemInline]
