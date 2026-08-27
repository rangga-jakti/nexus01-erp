"""
core/context_processors.py

Inject variabel ke SEMUA template tanpa perlu pass manual dari setiap view.
Ini yang bikin template bisa akses {{ active_company }}, {{ notifications }}, dll.
"""

from django.conf import settings


def nexus_context(request):
    """
    Context yang tersedia di semua template Nexus-01.
    """
    context = {
        'NEXUS_VERSION': settings.NEXUS_VERSION,
        'NEXUS_COMPANY_NAME': settings.NEXUS_COMPANY_NAME,
        'active_company': getattr(request, 'company', None),
        'active_permissions': getattr(request, 'active_permissions', set()),
    }

    if request.user.is_authenticated:
        # Daftar company yang bisa diakses user (untuk company switcher di navbar)
        try:
            user_companies = request.user.get_companies()
            context['user_companies'] = user_companies
        except Exception:
            context['user_companies'] = []

        # Notifikasi belum dibaca (untuk badge di navbar)
        try:
            from core.models import Notification
            unread_notifs = Notification.objects.filter(
                recipient=request.user,
                is_read=False,
                company=getattr(request, 'company', None),
            ).order_by('-created_at')[:10]
            context['unread_notifications'] = unread_notifs
            context['unread_count'] = unread_notifs.count()
        except Exception:
            context['unread_notifications'] = []
            context['unread_count'] = 0

    return context
