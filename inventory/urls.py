from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Product
    path('products/', views.product_list, name='product_list'),
    path('products/create/', views.product_create, name='product_create'),
    path('products/<uuid:uid>/', views.product_detail, name='product_detail'),
    path('products/<uuid:uid>/edit/', views.product_edit, name='product_edit'),
    path('products/<uuid:uid>/delete/', views.product_delete, name='product_delete'),

    # Warehouse
    path('warehouses/', views.warehouse_list, name='warehouse_list'),
    path('warehouses/create/', views.warehouse_create, name='warehouse_create'),
    path('warehouses/<uuid:uid>/', views.warehouse_detail, name='warehouse_detail'),
    path('warehouses/<uuid:uid>/edit/', views.warehouse_edit, name='warehouse_edit'),

    # Stock
    path('stock/', views.stock_list, name='stock_list'),
    path('stock/<int:stock_id>/adjust/', views.stock_adjust, name='stock_adjust'),

    # Movements
    path('movements/', views.movement_list, name='movement_list'),

    # HTMX
    path('htmx/product-search/', views.htmx_product_search, name='htmx_product_search'),
    path('htmx/stock-badge/<int:product_id>/', views.htmx_stock_badge, name='htmx_stock_badge'),
]

# Export URLs
from .exports import export_stock_excel, export_stock_pdf, export_movement_excel
urlpatterns += [
    path('export/stock/excel/', export_stock_excel, name='export_stock_excel'),
    path('export/stock/pdf/', export_stock_pdf, name='export_stock_pdf'),
    path('export/movements/excel/', export_movement_excel, name='export_movement_excel'),
]
