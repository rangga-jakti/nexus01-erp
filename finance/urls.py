from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/<uuid:uid>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<uuid:invoice_uid>/pay/', views.payment_create, name='payment_create'),
    path('payments/', views.payment_list, name='payment_list'),
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/create/', views.expense_create, name='expense_create'),
]

# Export URLs
from .exports import export_invoice_excel, export_invoice_pdf, export_expense_excel, export_payment_excel
urlpatterns += [
    path('export/invoices/excel/', export_invoice_excel, name='export_invoice_excel'),
    path('export/invoices/<uuid:uid>/pdf/', export_invoice_pdf, name='export_invoice_pdf'),
    path('export/expenses/excel/', export_expense_excel, name='export_expense_excel'),
    path('export/payments/excel/', export_payment_excel, name='export_payment_excel'),
]
