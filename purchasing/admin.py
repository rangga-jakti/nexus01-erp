from django.contrib import admin
from .models import Supplier, PurchaseRequest, PurchaseRequestItem, PurchaseOrder, PurchaseOrderItem, GoodsReceipt, GoodsReceiptItem

class PRItemInline(admin.TabularInline):
    model = PurchaseRequestItem
    extra = 1
    fields = ['product', 'description', 'quantity', 'unit', 'estimated_price', 'notes']

class POItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1
    fields = ['product', 'quantity', 'unit', 'unit_price', 'quantity_received']
    readonly_fields = ['quantity_received']

class GRItemInline(admin.TabularInline):
    model = GoodsReceiptItem
    extra = 1
    fields = ['po_item', 'quantity_received', 'notes']

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'city', 'phone', 'payment_terms_days', 'is_active']
    search_fields = ['name', 'code']

@admin.register(PurchaseRequest)
class PRAdmin(admin.ModelAdmin):
    list_display = ['number', 'title', 'status', 'company', 'created_by', 'total_amount', 'created_at']
    list_filter = ['status', 'company']
    search_fields = ['number', 'title']
    inlines = [PRItemInline]
    readonly_fields = ['number', 'uid', 'created_at', 'submitted_at', 'approved_at']

@admin.register(PurchaseOrder)
class POAdmin(admin.ModelAdmin):
    list_display = ['number', 'supplier', 'status', 'total_amount', 'order_date']
    list_filter = ['status', 'company']
    search_fields = ['number', 'supplier__name']
    inlines = [POItemInline]
    readonly_fields = ['number', 'uid', 'created_at']

@admin.register(GoodsReceipt)
class GRAdmin(admin.ModelAdmin):
    list_display = ['number', 'po', 'warehouse', 'status', 'receipt_date']
    list_filter = ['status', 'company']
    inlines = [GRItemInline]
    readonly_fields = ['number', 'uid', 'created_at', 'confirmed_at']
