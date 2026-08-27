"""finance/views.py — Invoice, Payment, Expense"""
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.utils import timezone
from core.models import AuditLog
from .models import Invoice, Payment, Expense


def require_company(view_func):
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.company:
            return redirect('core:select_company')
        return view_func(request, *args, **kwargs)
    return wrapper


# ── INVOICE ───────────────────────────────────────────────────────────────────

@login_required
@require_company
def invoice_list(request):
    inv_type = request.GET.get('type', '')
    status = request.GET.get('status', '')
    q = request.GET.get('q', '').strip()
    qs = Invoice.objects.filter(company=request.company).select_related('supplier', 'customer')
    if inv_type:
        qs = qs.filter(invoice_type=inv_type)
    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(Q(number__icontains=q))
    page = Paginator(qs.order_by('-created_at'), 20).get_page(request.GET.get('page', 1))
    # Stats
    stats = {
        'total_receivable': Invoice.objects.filter(company=request.company, invoice_type='SALES', status__in=['ISSUED','PARTIAL','OVERDUE']).aggregate(t=Sum('subtotal'))['t'] or 0,
        'total_payable': Invoice.objects.filter(company=request.company, invoice_type='PURCHASE', status__in=['ISSUED','PARTIAL','OVERDUE']).aggregate(t=Sum('subtotal'))['t'] or 0,
        'overdue': Invoice.objects.filter(company=request.company, due_date__lt=timezone.now().date(), status__in=['ISSUED','PARTIAL']).count(),
    }
    return render(request, 'finance/invoice_list.html', {
        'page_title': 'Invoice', 'invoices': page,
        'inv_type': inv_type, 'selected_status': status, 'q': q,
        'inv_types': Invoice.InvoiceType.choices, 'statuses': Invoice.Status.choices,
        'stats': stats,
    })


@login_required
@require_company
def invoice_detail(request, uid):
    invoice = get_object_or_404(Invoice, uid=uid, company=request.company)
    payments = invoice.payments.order_by('-payment_date')
    return render(request, 'finance/invoice_detail.html', {
        'page_title': invoice.number, 'invoice': invoice, 'payments': payments,
    })


@login_required
@require_company
@require_POST
def payment_create(request, invoice_uid):
    invoice = get_object_or_404(Invoice, uid=invoice_uid, company=request.company)
    amount = request.POST.get('amount', '0')
    method = request.POST.get('payment_method', 'TRANSFER')
    notes = request.POST.get('notes', '')
    ref = request.POST.get('reference_number', '')
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        messages.error(request, 'Jumlah pembayaran tidak valid.')
        return redirect('finance:invoice_detail', uid=invoice.uid)

    payment = Payment.objects.create(
        company=request.company,
        invoice=invoice,
        amount=amount,
        payment_method=method,
        notes=notes,
        reference_number=ref,
        status=Payment.Status.CONFIRMED,
        confirmed_at=timezone.now(),
        created_by=request.user,
    )
    invoice.update_status()
    AuditLog.log(user=request.user, action=AuditLog.Action.CREATE,
                obj=payment, company=request.company,
                message=f'Payment {payment.number} Rp {amount:,.0f} untuk {invoice.number}')
    messages.success(request, f'Payment {payment.number} berhasil dicatat.')
    return redirect('finance:invoice_detail', uid=invoice.uid)


@login_required
@require_company
def payment_list(request):
    qs = Payment.objects.filter(company=request.company).select_related('invoice').order_by('-payment_date')
    page = Paginator(qs, 25).get_page(request.GET.get('page', 1))
    return render(request, 'finance/payment_list.html', {'page_title': 'Payment', 'payments': page})


@login_required
@require_company
def expense_list(request):
    cat = request.GET.get('category', '')
    status = request.GET.get('status', '')
    qs = Expense.objects.filter(company=request.company)
    if cat:
        qs = qs.filter(category=cat)
    if status:
        qs = qs.filter(status=status)
    page = Paginator(qs.order_by('-expense_date'), 25).get_page(request.GET.get('page', 1))
    total = qs.aggregate(t=Sum('amount'))['t'] or 0
    return render(request, 'finance/expense_list.html', {
        'page_title': 'Expense', 'expenses': page,
        'categories': Expense.Category.choices, 'statuses': Expense.Status.choices,
        'selected_category': cat, 'selected_status': status, 'total': total,
    })


@login_required
@require_company
def expense_create(request):
    if request.method == 'POST':
        title = request.POST.get('title', '')
        category = request.POST.get('category', 'OTHER')
        amount = request.POST.get('amount', 0)
        date = request.POST.get('expense_date', timezone.now().date())
        notes = request.POST.get('description', '')
        try:
            expense = Expense.objects.create(
                company=request.company,
                title=title, category=category,
                amount=float(amount),
                expense_date=date,
                description=notes,
                created_by=request.user,
            )
            messages.success(request, f'Expense {expense.number} berhasil dibuat.')
            return redirect('finance:expense_list')
        except Exception as e:
            messages.error(request, str(e))
    return render(request, 'finance/expense_form.html', {
        'page_title': 'Buat Expense',
        'categories': Expense.Category.choices,
    })
