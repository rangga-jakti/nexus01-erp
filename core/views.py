"""
core/views.py — Dashboard dan shared views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages


@login_required
def dashboard(request):
    """
    Main dashboard — entry point setelah login.
    Data yang ditampilkan disesuaikan dengan role & company aktif.
    """
    if not request.company:
        return redirect('core:select_company')

    from accounts.models import UserCompany
    from core.models import ApprovalRequest, Notification

    context = {
        'page_title': 'Dashboard',
        # Pending approvals untuk user ini
        'pending_approvals': ApprovalRequest.objects.filter(
            approver=request.user,
            company=request.company,
            status=ApprovalRequest.Status.PENDING,
        ).select_related('requested_by')[:5],
        # Stats — akan diisi saat modul lain sudah ada
        'stats': _get_dashboard_stats(request),
    }
    return render(request, 'core/dashboard.html', context)


def _get_dashboard_stats(request):
    from django.db import models
    """Kumpulkan stats untuk dashboard. Aman jika modul belum ada."""
    stats = {}
    company = request.company

    try:
        from inventory.models import Product, Stock
        stats['total_products'] = Product.objects.filter(company=company, is_active=True).count()
        from django.db.models import F
        low_stock = Stock.objects.filter(
            company=company,
            quantity__lte=F('product__minimum_stock'),
        ).count()
        stats['low_stock_alerts'] = low_stock
    except Exception:
        stats['total_products'] = 0
        stats['low_stock_alerts'] = 0

    try:
        from purchasing.models import PurchaseRequest
        stats['pending_pr'] = PurchaseRequest.objects.filter(
            company=company, status='PENDING'
        ).count()
    except Exception:
        stats['pending_pr'] = 0

    try:
        from finance.models import Invoice
        from django.utils import timezone
        stats['overdue_invoices'] = Invoice.objects.filter(
            company=company,
            status='UNPAID',
            due_date__lt=timezone.now().date(),
        ).count()
    except Exception:
        stats['overdue_invoices'] = 0

    return stats


@login_required
def select_company(request):
    """Halaman pilih company aktif."""
    if request.method == 'POST':
        company_id = request.POST.get('company_id')
        companies = request.user.get_companies()

        try:
            company = companies.get(pk=company_id)
            request.session['active_company_id'] = company.pk
            messages.success(request, f'Switched to {company.name}')
            next_url = request.POST.get('next', 'core:dashboard')
            return redirect(next_url)
        except Exception:
            messages.error(request, 'Company tidak valid atau tidak punya akses.')

    companies = request.user.get_companies()

    # Auto-redirect kalau cuma punya 1 company
    if companies.count() == 1:
        company = companies.first()
        request.session['active_company_id'] = company.pk
        return redirect('core:dashboard')

    return render(request, 'core/select_company.html', {
        'companies': companies,
        'page_title': 'Pilih Perusahaan',
    })


@login_required
def notifications(request):
    from core.models import Notification
    notifs = Notification.objects.filter(
        recipient=request.user,
        company=request.company,
    ).order_by('-created_at')[:50]
    return render(request, 'core/notifications.html', {
        'notifications': notifs,
        'page_title': 'Notifikasi',
    })


@login_required
@require_POST
def mark_notification_read(request, pk):
    from core.models import Notification
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notif.mark_read()
    if request.htmx:
        return render(request, 'core/partials/notification_item.html', {'notif': notif})
    return redirect('core:notifications')


@login_required
def audit_log(request):
    """Audit log viewer — hanya untuk superuser atau role dengan permission khusus."""
    from core.models import AuditLog
    if not request.user.is_superuser and \
       not request.user.has_nexus_perm('core.view_audit_log', request.company):
        messages.error(request, 'Tidak punya akses ke Audit Log.')
        return redirect('core:dashboard')

    logs = AuditLog.objects.filter(
        company=request.company
    ).select_related('user', 'content_type').order_by('-timestamp')[:200]

    return render(request, 'core/audit_log.html', {
        'logs': logs,
        'page_title': 'Audit Log',
    })
