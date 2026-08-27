from django.contrib import admin
from .models import Customer, Quotation, QuotationItem, SalesOrder, SalesOrderItem, Delivery, DeliveryItem

class QuotationItemInline(admin.TabularInline):
    model = QuotationItem
    extra = 1

class SOItemInline(admin.TabularInline):
    model = SalesOrderItem
    extra = 1
    readonly_fields = ['quantity_delivered']

class DeliveryItemInline(admin.TabularInline):
    model = DeliveryItem
    extra = 1

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'city', 'phone', 'payment_terms_days', 'is_active']
    search_fields = ['name', 'code']

@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ['number', 'customer', 'status', 'quotation_date', 'total_amount']
    list_filter = ['status', 'company']
    inlines = [QuotationItemInline]

@admin.register(SalesOrder)
class SOAdmin(admin.ModelAdmin):
    list_display = ['number', 'customer', 'status', 'total_amount', 'order_date']
    list_filter = ['status', 'company']
    inlines = [SOItemInline]

@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ['number', 'so', 'warehouse', 'status', 'delivery_date']
    list_filter = ['status', 'company']
    inlines = [DeliveryItemInline]
