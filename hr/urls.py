from django.urls import path
from . import views

app_name = 'hr'

urlpatterns = [
    # Employee
    path('employees/', views.employee_list, name='employee_list'),
    path('employees/create/', views.employee_create, name='employee_create'),
    path('employees/<uuid:uid>/', views.employee_detail, name='employee_detail'),
    path('employees/<uuid:uid>/edit/', views.employee_edit, name='employee_edit'),

    # Attendance
    path('attendance/', views.attendance_list, name='attendance_list'),
    path('attendance/create/', views.attendance_create, name='attendance_create'),
    path('attendance/bulk/', views.attendance_bulk, name='attendance_bulk'),

    # Leave
    path('leave/', views.leave_list, name='leave_list'),
    path('leave/create/', views.leave_create, name='leave_create'),
    path('leave/<uuid:uid>/', views.leave_detail, name='leave_detail'),
    path('leave/<uuid:uid>/submit/', views.leave_submit, name='leave_submit'),
    path('leave/<uuid:uid>/approve/', views.leave_approve, name='leave_approve'),
    path('leave/<uuid:uid>/reject/', views.leave_reject, name='leave_reject'),

    # Payroll
    path('payroll/', views.payroll_list, name='payroll_list'),
    path('payroll/create/', views.payroll_create, name='payroll_create'),
    path('payroll/<uuid:uid>/', views.payroll_detail, name='payroll_detail'),
    path('payroll/<uuid:uid>/calculate/', views.payroll_calculate, name='payroll_calculate'),
    path('payroll/<uuid:uid>/approve/', views.payroll_approve, name='payroll_approve'),
    path('payroll/<uuid:uid>/export/excel/', views.payroll_export_excel, name='payroll_export_excel'),
    path('payroll/<uuid:uid>/employee/<uuid:emp_uid>/', views.payroll_detail_employee, name='payroll_detail_employee'),
    path('payroll/<uuid:payroll_uid>/slip/<uuid:emp_uid>/pdf/', views.payslip_pdf, name='payslip_pdf'),
]
