from django.urls import path
from . import views

app_name = 'purchasing'

urlpatterns = [
    # Supplier
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/create/', views.supplier_create, name='supplier_create'),
    path('suppliers/<uuid:uid>/edit/', views.supplier_edit, name='supplier_edit'),

    # Purchase Request
    path('pr/', views.pr_list, name='pr_list'),
    path('pr/create/', views.pr_create, name='pr_create'),
    path('pr/<uuid:uid>/', views.pr_detail, name='pr_detail'),
    path('pr/<uuid:uid>/submit/', views.pr_submit, name='pr_submit'),
    path('pr/<uuid:uid>/approve/', views.pr_approve, name='pr_approve'),
    path('pr/<uuid:uid>/reject/', views.pr_reject, name='pr_reject'),

    # Purchase Order
    path('po/', views.po_list, name='po_list'),
    path('po/from-pr/<uuid:pr_uid>/', views.po_create_from_pr, name='po_create_from_pr'),
    path('po/<uuid:uid>/', views.po_detail, name='po_detail'),
    path('po/<uuid:uid>/send/', views.po_send, name='po_send'),

    # Goods Receipt
    path('gr/', views.gr_list, name='gr_list'),
    path('gr/create/<uuid:po_uid>/', views.gr_create, name='gr_create'),
    path('gr/<uuid:uid>/', views.gr_detail, name='gr_detail'),
    path('gr/<uuid:uid>/confirm/', views.gr_confirm, name='gr_confirm'),
]

# Export URLs
from .exports import export_pr_excel, export_po_excel, export_po_pdf
urlpatterns += [
    path('export/pr/excel/', export_pr_excel, name='export_pr_excel'),
    path('export/po/excel/', export_po_excel, name='export_po_excel'),
    path('export/po/<uuid:po_uid>/pdf/', export_po_pdf, name='export_po_pdf'),
]
