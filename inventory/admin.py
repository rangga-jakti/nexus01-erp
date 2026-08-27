from django.contrib import admin
from .models import Product, ProductCategory, UnitOfMeasure, Warehouse, Stock, StockMovement

@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'company', 'parent', 'is_active']
    list_filter = ['company', 'is_active']

@admin.register(UnitOfMeasure)
class UOMAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'symbol', 'company']
    list_filter = ['company']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['sku', 'name', 'product_type', 'category', 'purchase_price', 'selling_price', 'total_stock', 'is_active']
    list_filter = ['company', 'product_type', 'is_active']
    search_fields = ['sku', 'name', 'barcode']
    readonly_fields = ['uid', 'created_at', 'updated_at']

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'company', 'branch', 'is_default', 'is_active']
    list_filter = ['company', 'is_active']

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ['product', 'warehouse', 'quantity', 'reserved_quantity', 'available_quantity', 'last_movement_at']
    list_filter = ['company', 'warehouse']
    search_fields = ['product__name', 'product__sku']
    readonly_fields = ['quantity', 'reserved_quantity', 'last_movement_at', 'uid', 'created_at']

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'product', 'warehouse', 'movement_type', 'quantity', 'quantity_before', 'quantity_after', 'reference']
    list_filter = ['movement_type', 'company', 'warehouse']
    search_fields = ['product__name', 'reference']
    readonly_fields = ['created_at', 'quantity_before', 'quantity_after']
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
