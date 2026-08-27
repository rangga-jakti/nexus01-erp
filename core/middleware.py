"""
core/middleware.py

Dua middleware penting:
1. ActiveCompanyMiddleware — inject request.company ke setiap request
2. AuditLogMiddleware — log semua write operations
"""

from django.utils import timezone
from django.shortcuts import redirect
from django.urls import reverse, resolve
from django.contrib import messages


class ActiveCompanyMiddleware:
    """
    Inject request.company ke setiap request berdasarkan session user.

    Flow:
    1. User login → pilih company (atau auto-select default)
    2. company.pk disimpan di session['active_company_id']
    3. Middleware ini baca session tersebut dan set request.company
    4. Semua view bisa akses request.company tanpa perlu query ulang

    Kenapa session, bukan URL prefix?
    - URL prefix (/company-id/purchasing/...) lebih RESTful tapi verbose
    - Session lebih simple untuk internal ERP yang tidak butuh bookmark per company
    - User bisa switch company dari navbar tanpa reload halaman
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.company = None
        request.active_permissions = set()

        if request.user.is_authenticated:
            from organization.models import Company
            from accounts.models import UserCompany

            company_id = request.session.get('active_company_id')

            if company_id:
                try:
                    company = Company.objects.get(pk=company_id, is_active=True)
                    # Validasi: user memang punya akses ke company ini
                    if request.user.is_superuser or \
                       UserCompany.objects.filter(user=request.user, company=company, is_active=True).exists():
                        request.company = company
                    else:
                        # User tidak punya akses, clear session
                        del request.session['active_company_id']
                except Company.DoesNotExist:
                    pass

            # Kalau belum ada active company, set ke default
            if request.company is None:
                default_company = UserCompany.get_default_company(request.user)
                if default_company:
                    request.company = default_company
                    request.session['active_company_id'] = default_company.pk

            # Cache permissions user di company aktif ini
            if request.company:
                request.active_permissions = request.user.get_all_permissions_in_company(request.company)

        response = self.get_response(request)
        return response


class AuditLogMiddleware:
    """
    Log semua POST/PUT/PATCH/DELETE requests ke AuditLog.

    Catatan: Middleware ini hanya log HTTP method dan URL.
    Untuk log perubahan field spesifik, gunakan AuditLog.log() di view/signal.
    Middleware ini sebagai safety net — pastikan tidak ada yang lolos.
    """

    # URL yang tidak perlu di-log (terlalu noisy)
    EXCLUDED_PATHS = [
        '/static/', '/media/', '/favicon.ico',
        '/admin/jsi18n/', '/admin/autocomplete/',
    ]

    WRITE_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Log hanya write operations dari authenticated user
        if (request.method in self.WRITE_METHODS and
                request.user.is_authenticated and
                not any(request.path.startswith(p) for p in self.EXCLUDED_PATHS) and
                response.status_code < 500):

            # Import di sini untuk menghindari circular import saat startup
            try:
                from core.models import AuditLog
                AuditLog.objects.create(
                    user=request.user,
                    company=getattr(request, 'company', None),
                    action=AuditLog.Action.CREATE if request.method == 'POST' else AuditLog.Action.UPDATE,
                    message=f"{request.method} {request.path} → {response.status_code}",
                    ip_address=self._get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                )
            except Exception:
                # Audit log tidak boleh crash aplikasi utama
                pass

        return response

    def _get_client_ip(self, request):
        """Ambil IP client yang benar, handle proxy/load balancer."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
