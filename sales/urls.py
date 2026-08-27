from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/create/', views.customer_create, name='customer_create'),
    path('customers/<uuid:uid>/edit/', views.customer_edit, name='customer_edit'),

    path('quotations/', views.quotation_list, name='quotation_list'),
    path('quotations/create/', views.quotation_create, name='quotation_create'),
    path('quotations/<uuid:uid>/', views.quotation_detail, name='quotation_detail'),
    path('quotations/<uuid:uid>/convert/', views.quotation_convert, name='quotation_convert'),

    path('orders/', views.so_list, name='so_list'),
    path('orders/create/', views.so_create, name='so_create'),
    path('orders/<uuid:uid>/', views.so_detail, name='so_detail'),
    path('orders/<uuid:uid>/confirm/', views.so_confirm, name='so_confirm'),

    path('deliveries/', views.delivery_list, name='delivery_list'),
    path('deliveries/create/<uuid:so_uid>/', views.delivery_create, name='delivery_create'),
    path('deliveries/<uuid:uid>/', views.delivery_detail, name='delivery_detail'),
    path('deliveries/<uuid:uid>/confirm/', views.delivery_confirm, name='delivery_confirm'),
]

# Export URLs
from .exports import export_so_excel, export_so_pdf, export_customer_excel
urlpatterns += [
    path('export/so/excel/', export_so_excel, name='export_so_excel'),
    path('export/so/<uuid:so_uid>/pdf/', export_so_pdf, name='export_so_pdf'),
    path('export/customers/excel/', export_customer_excel, name='export_customer_excel'),
]
