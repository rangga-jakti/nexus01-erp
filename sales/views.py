"""sales/views.py — Customer, Quotation, SalesOrder, Delivery"""
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.utils import timezone
from core.models import AuditLog
from .models import Customer, Quotation, QuotationItem, SalesOrder, SalesOrderItem, Delivery, DeliveryItem
from .forms import CustomerForm, QuotationForm, QuotationItemFormSet, SalesOrderForm, DeliveryForm


def require_company(view_func):
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.company:
            return redirect('core:select_company')
        return view_func(request, *args, **kwargs)
    return wrapper


# ── CUSTOMER ─────────────────────────────────────────────────────────────────

@login_required
@require_company
def customer_list(request):
    q = request.GET.get('q', '').strip()
    qs = Customer.objects.filter(company=request.company, is_active=True)
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q) | Q(city__icontains=q))
    page = Paginator(qs.order_by('name'), 25).get_page(request.GET.get('page', 1))
    return render(request, 'sales/customer_list.html', {'page_title': 'Customer', 'customers': page, 'q': q})


@login_required
@require_company
def customer_create(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            c = form.save(commit=False)
            c.company = request.company
            c.created_by = request.user
            c.save()
            messages.success(request, f'Customer "{c.name}" berhasil dibuat.')
            return redirect('sales:customer_list')
    else:
        form = CustomerForm()
    return render(request, 'sales/customer_form.html', {'page_title': 'Tambah Customer', 'form': form})


@login_required
@require_company
def customer_edit(request, uid):
    customer = get_object_or_404(Customer, uid=uid, company=request.company)
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Customer diupdate.')
            return redirect('sales:customer_list')
    else:
        form = CustomerForm(instance=customer)
    return render(request, 'sales/customer_form.html', {'page_title': f'Edit: {customer.name}', 'form': form, 'customer': customer})


# ── QUOTATION ─────────────────────────────────────────────────────────────────

@login_required
@require_company
def quotation_list(request):
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    qs = Quotation.objects.filter(company=request.company).select_related('customer')
    if q:
        qs = qs.filter(Q(number__icontains=q) | Q(customer__name__icontains=q))
    if status:
        qs = qs.filter(status=status)
    page = Paginator(qs.order_by('-created_at'), 20).get_page(request.GET.get('page', 1))
    return render(request, 'sales/quotation_list.html', {
        'page_title': 'Quotation', 'quotations': page,
        'q': q, 'selected_status': status, 'statuses': Quotation.Status.choices,
    })


@login_required
@require_company
def quotation_create(request):
    if request.method == 'POST':
        form = QuotationForm(request.POST, company=request.company)
        formset = QuotationItemFormSet(request.POST, form_kwargs={'company': request.company})
        if form.is_valid() and formset.is_valid():
            qt = form.save(commit=False)
            qt.company = request.company
            qt.created_by = request.user
            qt.save()
            formset.instance = qt
            formset.save()
            messages.success(request, f'Quotation {qt.number} berhasil dibuat.')
            return redirect('sales:quotation_detail', uid=qt.uid)
    else:
        form = QuotationForm(company=request.company)
        formset = QuotationItemFormSet(form_kwargs={'company': request.company})
    return render(request, 'sales/quotation_form.html', {
        'page_title': 'Buat Quotation', 'form': form, 'formset': formset,
    })


@login_required
@require_company
def quotation_detail(request, uid):
    qt = get_object_or_404(Quotation, uid=uid, company=request.company)
    return render(request, 'sales/quotation_detail.html', {
        'page_title': qt.number, 'qt': qt,
        'items': qt.items.select_related('product', 'unit'),
    })


@login_required
@require_company
@require_POST
def quotation_convert(request, uid):
    """Convert quotation yang diterima menjadi Sales Order."""
    qt = get_object_or_404(Quotation, uid=uid, company=request.company)
    if qt.status not in [Quotation.Status.DRAFT, Quotation.Status.SENT]:
        messages.error(request, 'Quotation sudah tidak bisa dikonversi.')
        return redirect('sales:quotation_detail', uid=qt.uid)

    so = SalesOrder.objects.create(
        company=request.company,
        quotation=qt,
        customer=qt.customer,
        branch=qt.branch,
        tax_rate=qt.tax_rate,
        discount_amount=qt.discount_amount,
        created_by=request.user,
    )
    for item in qt.items.select_related('product', 'unit'):
        SalesOrderItem.objects.create(
            so=so, product=item.product,
            description=item.description,
            quantity=item.quantity, unit=item.unit,
            unit_price=item.unit_price,
        )
    qt.status = Quotation.Status.ACCEPTED
    qt.save(update_fields=['status'])

    AuditLog.log(user=request.user, action=AuditLog.Action.CREATE,
                obj=so, company=request.company,
                message=f'SO {so.number} dibuat dari Quotation {qt.number}')
    messages.success(request, f'Sales Order {so.number} berhasil dibuat dari {qt.number}.')
    return redirect('sales:so_detail', uid=so.uid)


# ── SALES ORDER ───────────────────────────────────────────────────────────────

@login_required
@require_company
def so_list(request):
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    qs = SalesOrder.objects.filter(company=request.company).select_related('customer')
    if q:
        qs = qs.filter(Q(number__icontains=q) | Q(customer__name__icontains=q))
    if status:
        qs = qs.filter(status=status)
    page = Paginator(qs.order_by('-created_at'), 20).get_page(request.GET.get('page', 1))
    return render(request, 'sales/so_list.html', {
        'page_title': 'Sales Order', 'sos': page,
        'q': q, 'selected_status': status, 'statuses': SalesOrder.Status.choices,
    })


@login_required
@require_company
def so_create(request):
    if request.method == 'POST':
        form = SalesOrderForm(request.POST, company=request.company)
        if form.is_valid():
            so = form.save(commit=False)
            so.company = request.company
            so.created_by = request.user
            so.save()
            messages.success(request, f'Sales Order {so.number} berhasil dibuat.')
            return redirect('sales:so_detail', uid=so.uid)
    else:
        form = SalesOrderForm(company=request.company)
    return render(request, 'sales/so_form.html', {'page_title': 'Buat Sales Order', 'form': form})


@login_required
@require_company
def so_detail(request, uid):
    so = get_object_or_404(SalesOrder, uid=uid, company=request.company)
    items = so.items.select_related('product', 'unit')
    deliveries = so.deliveries.select_related('warehouse').order_by('-created_at')
    return render(request, 'sales/so_detail.html', {
        'page_title': so.number, 'so': so, 'items': items, 'deliveries': deliveries,
    })


@login_required
@require_company
@require_POST
def so_confirm(request, uid):
    so = get_object_or_404(SalesOrder, uid=uid, company=request.company, status='DRAFT')
    so.status = SalesOrder.Status.CONFIRMED
    so.save(update_fields=['status'])
    messages.success(request, f'SO {so.number} dikonfirmasi.')
    return redirect('sales:so_detail', uid=so.uid)


# ── DELIVERY ──────────────────────────────────────────────────────────────────

@login_required
@require_company
def delivery_list(request):
    qs = Delivery.objects.filter(company=request.company).select_related('so__customer', 'warehouse').order_by('-created_at')
    page = Paginator(qs, 20).get_page(request.GET.get('page', 1))
    return render(request, 'sales/delivery_list.html', {'page_title': 'Delivery', 'deliveries': page})


@login_required
@require_company
def delivery_create(request, so_uid):
    so = get_object_or_404(SalesOrder, uid=so_uid, company=request.company)
    if so.status not in [SalesOrder.Status.CONFIRMED, SalesOrder.Status.PARTIAL]:
        messages.error(request, 'SO belum dikonfirmasi.')
        return redirect('sales:so_detail', uid=so.uid)

    if request.method == 'POST':
        form = DeliveryForm(request.POST, company=request.company)
        if form.is_valid():
            delivery = form.save(commit=False)
            delivery.company = request.company
            delivery.so = so
            delivery.created_by = request.user
            delivery.save()

            for item in so.items.select_related('product'):
                qty_str = request.POST.get(f'qty_{item.pk}', '0')
                try:
                    qty = float(qty_str)
                except ValueError:
                    qty = 0
                if qty > 0:
                    DeliveryItem.objects.create(
                        delivery=delivery, so_item=item,
                        quantity=min(qty, item.quantity_pending),
                    )

            if not delivery.items.exists():
                delivery.delete()
                messages.error(request, 'Masukkan minimal 1 item dengan qty > 0.')
                return redirect(request.path)

            messages.success(request, f'Delivery {delivery.number} dibuat.')
            return redirect('sales:delivery_detail', uid=delivery.uid)
    else:
        form = DeliveryForm(company=request.company)

    pending_items = [i for i in so.items.select_related('product', 'unit') if i.quantity_pending > 0]
    return render(request, 'sales/delivery_form.html', {
        'page_title': f'Buat Delivery — {so.number}',
        'form': form, 'so': so, 'pending_items': pending_items,
    })


@login_required
@require_company
def delivery_detail(request, uid):
    delivery = get_object_or_404(Delivery, uid=uid, company=request.company)
    items = delivery.items.select_related('so_item__product', 'so_item__unit')
    return render(request, 'sales/delivery_detail.html', {
        'page_title': delivery.number, 'delivery': delivery, 'items': items,
    })


@login_required
@require_company
@require_POST
def delivery_confirm(request, uid):
    delivery = get_object_or_404(Delivery, uid=uid, company=request.company)
    try:
        delivery.confirm_delivery(request.user)
        messages.success(request, f'Delivery {delivery.number} dikonfirmasi. Stok berkurang.')
    except (ValueError, Exception) as e:
        messages.error(request, str(e))
    return redirect('sales:delivery_detail', uid=delivery.uid)
