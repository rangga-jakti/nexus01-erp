from django.contrib import admin
from .models import Invoice, Payment, Expense

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['number', 'invoice_type', 'status', 'total_amount', 'paid_amount', 'outstanding_amount', 'due_date']
    list_filter = ['invoice_type', 'status', 'company']
    search_fields = ['number']
    readonly_fields = ['number', 'uid', 'created_at']

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['number', 'invoice', 'amount', 'payment_method', 'status', 'payment_date']
    list_filter = ['status', 'payment_method', 'company']
    readonly_fields = ['number', 'uid', 'created_at', 'confirmed_at']

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['number', 'title', 'category', 'status', 'amount', 'expense_date']
    list_filter = ['status', 'category', 'company']
    readonly_fields = ['number', 'uid', 'created_at']
