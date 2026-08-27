"""hr/forms.py"""
from django import forms
from .models import (Employee, JobPosition, WorkSchedule, Attendance,
                     LeaveType, LeaveRequest, PayrollComponent, Payroll, PayrollDetail, PayrollItem)


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            'employee_id', 'first_name', 'last_name', 'gender', 'birth_date', 'birth_place',
            'nationality', 'religion', 'marital_status', 'dependents',
            'nik', 'npwp', 'bpjs_kes', 'bpjs_tk', 'tax_status',
            'email', 'phone', 'address', 'city', 'emergency_contact', 'emergency_phone',
            'branch', 'department', 'position', 'direct_manager', 'employment_status',
            'join_date', 'end_date', 'bank_name', 'bank_account', 'bank_account_name',
            'basic_salary', 'photo', 'notes', 'user',
        ]
        widgets = {
            'employee_id': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'EMP-001'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'birth_place': forms.TextInput(attrs={'class': 'form-input'}),
            'nationality': forms.TextInput(attrs={'class': 'form-input'}),
            'religion': forms.TextInput(attrs={'class': 'form-input'}),
            'marital_status': forms.Select(attrs={'class': 'form-select'}),
            'dependents': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'nik': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '16 digit'}),
            'npwp': forms.TextInput(attrs={'class': 'form-input'}),
            'bpjs_kes': forms.TextInput(attrs={'class': 'form-input'}),
            'bpjs_tk': forms.TextInput(attrs={'class': 'form-input'}),
            'tax_status': forms.Select(attrs={'class': 'form-select'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'class': 'form-input'}),
            'address': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}),
            'city': forms.TextInput(attrs={'class': 'form-input'}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-input'}),
            'emergency_phone': forms.TextInput(attrs={'class': 'form-input'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'position': forms.Select(attrs={'class': 'form-select'}),
            'direct_manager': forms.Select(attrs={'class': 'form-select'}),
            'employment_status': forms.Select(attrs={'class': 'form-select'}),
            'join_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-input'}),
            'bank_account': forms.TextInput(attrs={'class': 'form-input'}),
            'bank_account_name': forms.TextInput(attrs={'class': 'form-input'}),
            'basic_salary': forms.NumberInput(attrs={'class': 'form-input', 'step': '1', 'min': '0'}),
            'notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}),
            'user': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            from organization.models import Branch, Department
            from accounts.models import User
            self.fields['branch'].queryset = Branch.objects.filter(company=company, is_active=True)
            self.fields['department'].queryset = Department.objects.filter(company=company, is_active=True)
            self.fields['position'].queryset = JobPosition.objects.filter(company=company, is_active=True)
            self.fields['direct_manager'].queryset = Employee.objects.filter(company=company, resign_date__isnull=True)
            self.fields['user'].queryset = User.objects.filter(
                usercompany__company=company
            ).distinct()

        optional = ['last_name', 'birth_date', 'birth_place', 'religion', 'nik', 'npwp',
                    'bpjs_kes', 'bpjs_tk', 'email', 'phone', 'address', 'city',
                    'emergency_contact', 'emergency_phone', 'branch', 'department',
                    'position', 'direct_manager', 'end_date', 'bank_name', 'bank_account',
                    'bank_account_name', 'photo', 'notes', 'user']
        for f in optional:
            if f in self.fields:
                self.fields[f].required = False


class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['employee', 'date', 'schedule', 'status', 'check_in', 'check_out',
                  'check_in_location', 'check_out_location', 'overtime_minutes', 'notes']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'schedule': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'check_in': forms.TimeInput(attrs={'class': 'form-input', 'type': 'time'}),
            'check_out': forms.TimeInput(attrs={'class': 'form-input', 'type': 'time'}),
            'check_in_location': forms.TextInput(attrs={'class': 'form-input'}),
            'check_out_location': forms.TextInput(attrs={'class': 'form-input'}),
            'overtime_minutes': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            self.fields['employee'].queryset = Employee.objects.filter(
                company=company, resign_date__isnull=True
            )
            self.fields['schedule'].queryset = WorkSchedule.objects.filter(company=company, is_active=True)
        for f in ['schedule', 'check_in', 'check_out', 'check_in_location',
                  'check_out_location', 'overtime_minutes', 'notes']:
            self.fields[f].required = False


class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['employee', 'leave_type', 'start_date', 'end_date', 'reason', 'attachment']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'leave_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'reason': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3,
                                            'placeholder': 'Alasan pengajuan cuti'}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            self.fields['employee'].queryset = Employee.objects.filter(
                company=company, resign_date__isnull=True
            )
            self.fields['leave_type'].queryset = LeaveType.objects.filter(
                company=company, is_active=True
            )
        self.fields['attachment'].required = False


class PayrollForm(forms.ModelForm):
    class Meta:
        model = Payroll
        fields = ['name', 'period_month', 'period_year', 'branch', 'payment_date', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Gaji Agustus 2026'}),
            'period_month': forms.Select(
                attrs={'class': 'form-select'},
                choices=[(i, f"{i:02d} — {['Jan','Feb','Mar','Apr','Mei','Jun','Jul','Agu','Sep','Okt','Nov','Des'][i-1]}") for i in range(1, 13)]
            ),
            'period_year': forms.NumberInput(attrs={'class': 'form-input', 'min': '2020', 'max': '2099'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            from organization.models import Branch
            self.fields['branch'].queryset = Branch.objects.filter(company=company, is_active=True)
        self.fields['branch'].required = False
        self.fields['payment_date'].required = False
        self.fields['notes'].required = False


class PayrollItemForm(forms.ModelForm):
    """Form untuk edit komponen gaji per karyawan."""
    class Meta:
        model = PayrollItem
        fields = ['component', 'amount', 'notes']
        widgets = {
            'component': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-input', 'step': '1', 'min': '0'}),
            'notes': forms.TextInput(attrs={'class': 'form-input'}),
        }
