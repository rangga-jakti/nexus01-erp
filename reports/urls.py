from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.overview, name='overview'),
]

# Export URLs
from .exports import export_full_report_excel, export_full_report_pdf
urlpatterns += [
    path('export/excel/', export_full_report_excel, name='export_excel'),
    path('export/pdf/', export_full_report_pdf, name='export_pdf'),
]
