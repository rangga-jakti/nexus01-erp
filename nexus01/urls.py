"""
nexus01/urls.py — Root URL configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

admin.site.site_header = 'Nexus-01 ERP Admin'
admin.site.site_title = 'Nexus-01'
admin.site.index_title = 'Dashboard Admin'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls', namespace='core')),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('org/', include('organization.urls', namespace='organization')),
    path('inventory/', include('inventory.urls', namespace='inventory')),
    path('purchasing/', include('purchasing.urls', namespace='purchasing')),
    path('sales/', include('sales.urls', namespace='sales')),
    path('finance/', include('finance.urls', namespace='finance')),
    path('reports/', include('reports.urls', namespace='reports')),
    path('hr/', include('hr.urls', namespace='hr')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
