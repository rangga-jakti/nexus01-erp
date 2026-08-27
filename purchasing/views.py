"""
purchasing/views.py — Supplier, PR, PO, GoodsReceipt
Business flow: PR → Approval → PO → GR → Stock++
"""
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse

from .models import Supplier, PurchaseRequest, PurchaseRequestItem, PurchaseOrder, PurchaseOrderItem, GoodsReceipt, GoodsReceiptItem
from .forms import SupplierForm, PurchaseRequestForm, PurchaseRequestItemFormSet, PurchaseOrderForm, GoodsReceiptForm
from core.models import AuditLog


def require_company(view_func):
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.company:
            messages.warning(request, 'Pilih perusahaan terlebih dahulu.')
            return redirect('core:select_company')
        return view_func(request, *args, **kwargs)
    return wrapper


# ── SUPPLIER ────────────────────────────────────────────────────────────────

@login_required
@require_company
def supplier_list(request):
    q = request.GET.get('q', '').strip()
    qs = Supplier.objects.filter(company=request.company, is_active=True)
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q) | Q(city__icontains=q))
    qs = qs.order_by('name')
    page = Paginator(qs, 25).get_page(request.GET.get('page', 1))
    return render(request, 'purchasing/supplier_list.html', {
        'page_title': 'Supplier', 'suppliers': page, 'q': q,
    })


@login_required
@require_company
def supplier_create(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            s = form.save(commit=False)
            s.company = request.company
            s.created_by = request.user
            s.save()
            messages.success(request, f'Supplier "{s.name}" berhasil dibuat.')
            return redirect('purchasing:supplier_list')
    else:
        form = SupplierForm()
    return render(request, 'purchasing/supplier_form.html', {'page_title': 'Tambah Supplier', 'form': form})


@login_required
@require_company
def supplier_edit(request, uid):
    supplier = get_object_or_404(Supplier, uid=uid, company=request.company)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, 'Supplier diupdate.')
            return redirect('purchasing:supplier_list')
    else:
        form = SupplierForm(instance=supplier)
    return render(request, 'purchasing/supplier_form.html', {
        'page_title': f'Edit: {supplier.name}', 'form': form, 'supplier': supplier,
    })


# ── PURCHASE REQUEST ─────────────────────────────────────────────────────────

@login_required
@require_company
def pr_list(request):
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    qs = PurchaseRequest.objects.filter(company=request.company).select_related('created_by', 'suggested_supplier', 'department')
    if q:
        qs = qs.filter(Q(number__icontains=q) | Q(title__icontains=q))
    if status:
        qs = qs.filter(status=status)
    qs = qs.order_by('-created_at')
    page = Paginator(qs, 20).get_page(request.GET.get('page', 1))
    return render(request, 'purchasing/pr_list.html', {
        'page_title': 'Purchase Request',
        'prs': page, 'q': q, 'selected_status': status,
        'statuses': PurchaseRequest.Status.choices,
        'counts': {s.value: PurchaseRequest.objects.filter(company=request.company, status=s).count()
                   for s in PurchaseRequest.Status},
    })


@login_required
@require_company
def pr_create(request):
    if request.method == 'POST':
        form = PurchaseRequestForm(request.POST, company=request.company)
        formset = PurchaseRequestItemFormSet(request.POST, form_kwargs={'company': request.company})
        if form.is_valid() and formset.is_valid():
            pr = form.save(commit=False)
            pr.company = request.company
            pr.created_by = request.user
            pr.save()
            formset.instance = pr
            formset.save()
            AuditLog.log(user=request.user, action=AuditLog.Action.CREATE,
                        obj=pr, company=request.company, message=f'PR {pr.number} dibuat')
            messages.success(request, f'Purchase Request {pr.number} berhasil dibuat.')
            return redirect('purchasing:pr_detail', uid=pr.uid)
    else:
        form = PurchaseRequestForm(company=request.company)
        formset = PurchaseRequestItemFormSet(form_kwargs={'company': request.company})
    return render(request, 'purchasing/pr_form.html', {
        'page_title': 'Buat Purchase Request',
        'form': form, 'formset': formset, 'action': 'create',
    })


@login_required
@require_company
def pr_detail(request, uid):
    pr = get_object_or_404(PurchaseRequest, uid=uid, company=request.company)
    items = pr.items.select_related('product', 'unit').all()
    approval = None
    try:
        from core.models import ApprovalRequest
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(pr)
        approval = ApprovalRequest.objects.filter(content_type=ct, object_id=pr.pk).last()
    except Exception:
        pass
    return render(request, 'purchasing/pr_detail.html', {
        'page_title': pr.number, 'pr': pr, 'items': items, 'approval': approval,
    })


@login_required
@require_company
@require_POST
def pr_submit(request, uid):
    """Submit PR untuk approval."""
    pr = get_object_or_404(PurchaseRequest, uid=uid, company=request.company)
    if pr.status != PurchaseRequest.Status.DRAFT:
        messages.error(request, 'Hanya PR berstatus Draft yang bisa disubmit.')
        return redirect('purchasing:pr_detail', uid=pr.uid)
    if not pr.items.exists():
        messages.error(request, 'PR harus punya minimal 1 item sebelum disubmit.')
        return redirect('purchasing:pr_detail', uid=pr.uid)
    pr.submit_for_approval(request.user)
    messages.success(request, f'PR {pr.number} berhasil disubmit untuk approval.')
    return redirect('purchasing:pr_detail', uid=pr.uid)


@login_required
@require_company
@require_POST
def pr_approve(request, uid):
    pr = get_object_or_404(PurchaseRequest, uid=uid, company=request.company)
    if pr.status != PurchaseRequest.Status.PENDING:
        messages.error(request, 'PR tidak berstatus Pending.')
        return redirect('purchasing:pr_detail', uid=pr.uid)
    from django.utils import timezone as tz
    pr.status = PurchaseRequest.Status.APPROVED
    pr.approved_at = tz.now()
    pr.approved_by = request.user
    pr.save()
    AuditLog.log(user=request.user, action=AuditLog.Action.APPROVE,
                obj=pr, company=request.company)
    messages.success(request, f'PR {pr.number} disetujui.')
    return redirect('purchasing:pr_detail', uid=pr.uid)


@login_required
@require_company
@require_POST
def pr_reject(request, uid):
    pr = get_object_or_404(PurchaseRequest, uid=uid, company=request.company)
    reason = request.POST.get('reason', '').strip()
    if not reason:
        messages.error(request, 'Alasan penolakan wajib diisi.')
        return redirect('purchasing:pr_detail', uid=pr.uid)
    pr.status = PurchaseRequest.Status.REJECTED
    pr.rejection_reason = reason
    pr.save()
    AuditLog.log(user=request.user, action=AuditLog.Action.REJECT,
                obj=pr, company=request.company, message=reason)
    messages.success(request, f'PR {pr.number} ditolak.')
    return redirect('purchasing:pr_detail', uid=pr.uid)


# ── PURCHASE ORDER ───────────────────────────────────────────────────────────

@login_required
@require_company
def po_list(request):
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    qs = PurchaseOrder.objects.filter(company=request.company).select_related('supplier')
    if q:
        qs = qs.filter(Q(number__icontains=q) | Q(supplier__name__icontains=q))
    if status:
        qs = qs.filter(status=status)
    page = Paginator(qs.order_by('-created_at'), 20).get_page(request.GET.get('page', 1))
    return render(request, 'purchasing/po_list.html', {
        'page_title': 'Purchase Order',
        'pos': page, 'q': q, 'selected_status': status,
        'statuses': PurchaseOrder.Status.choices,
    })


@login_required
@require_company
def po_create_from_pr(request, pr_uid):
    """Buat PO dari PR yang sudah approved."""
    pr = get_object_or_404(PurchaseRequest, uid=pr_uid, company=request.company,
                           status=PurchaseRequest.Status.APPROVED)
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST, company=request.company)
        if form.is_valid():
            po = form.save(commit=False)
            po.company = request.company
            po.pr = pr
            po.created_by = request.user
            po.save()

            # Copy items dari PR ke PO
            for pr_item in pr.items.select_related('product', 'unit'):
                if pr_item.product:
                    PurchaseOrderItem.objects.create(
                        po=po,
                        pr_item=pr_item,
                        product=pr_item.product,
                        description=pr_item.description,
                        quantity=pr_item.quantity,
                        unit=pr_item.unit,
                        unit_price=pr_item.estimated_price,
                    )

            # Update PR status
            pr.status = PurchaseRequest.Status.PO_CREATED
            pr.save(update_fields=['status'])

            AuditLog.log(user=request.user, action=AuditLog.Action.CREATE,
                        obj=po, company=request.company, message=f'PO {po.number} dibuat dari PR {pr.number}')
            messages.success(request, f'Purchase Order {po.number} berhasil dibuat.')
            return redirect('purchasing:po_detail', uid=po.uid)
    else:
        form = PurchaseOrderForm(
            company=request.company,
            initial={'supplier': pr.suggested_supplier}
        )
    return render(request, 'purchasing/po_form.html', {
        'page_title': f'Buat PO dari {pr.number}',
        'form': form, 'pr': pr,
    })


@login_required
@require_company
def po_detail(request, uid):
    po = get_object_or_404(PurchaseOrder, uid=uid, company=request.company)
    items = po.items.select_related('product', 'unit')
    grs = po.goods_receipts.select_related('warehouse').order_by('-created_at')
    return render(request, 'purchasing/po_detail.html', {
        'page_title': po.number, 'po': po, 'items': items, 'grs': grs,
    })


@login_required
@require_company
@require_POST
def po_send(request, uid):
    po = get_object_or_404(PurchaseOrder, uid=uid, company=request.company, status='DRAFT')
    po.status = PurchaseOrder.Status.SENT
    po.sent_at = timezone.now()
    po.save()
    messages.success(request, f'PO {po.number} ditandai sudah dikirim ke supplier.')
    return redirect('purchasing:po_detail', uid=po.uid)


# ── GOODS RECEIPT ─────────────────────────────────────────────────────────

@login_required
@require_company
def gr_list(request):
    qs = GoodsReceipt.objects.filter(company=request.company).select_related('po__supplier', 'warehouse').order_by('-created_at')
    page = Paginator(qs, 20).get_page(request.GET.get('page', 1))
    return render(request, 'purchasing/gr_list.html', {
        'page_title': 'Goods Receipt', 'grs': page,
    })


@login_required
@require_company
def gr_create(request, po_uid):
    po = get_object_or_404(PurchaseOrder, uid=po_uid, company=request.company)
    if po.status not in [PurchaseOrder.Status.SENT, PurchaseOrder.Status.CONFIRMED, PurchaseOrder.Status.PARTIAL]:
        messages.error(request, 'PO belum dikirim ke supplier.')
        return redirect('purchasing:po_detail', uid=po.uid)

    if request.method == 'POST':
        form = GoodsReceiptForm(request.POST, company=request.company)
        if form.is_valid():
            gr = form.save(commit=False)
            gr.company = request.company
            gr.po = po
            gr.created_by = request.user
            gr.save()

            # Buat GR items dari PO items yang belum fully received
            for po_item in po.items.select_related('product'):
                if po_item.quantity_pending > 0:
                    qty_str = request.POST.get(f'qty_{po_item.pk}', '0')
                    try:
                        qty = float(qty_str)
                    except ValueError:
                        qty = 0
                    if qty > 0:
                        GoodsReceiptItem.objects.create(
                            gr=gr,
                            po_item=po_item,
                            quantity_received=min(qty, po_item.quantity_pending),
                        )

            if not gr.items.exists():
                gr.delete()
                messages.error(request, 'Masukkan minimal 1 item dengan qty > 0.')
                return redirect(request.path)

            messages.success(request, f'GR {gr.number} dibuat. Konfirmasi untuk update stok.')
            return redirect('purchasing:gr_detail', uid=gr.uid)
    else:
        form = GoodsReceiptForm(company=request.company)

    pending_items = po.items.filter(quantity__gt=Q(quantity_received=0) | Q(quantity__gt=0)).select_related('product', 'unit')
    pending_items = [item for item in po.items.select_related('product','unit') if item.quantity_pending > 0]

    return render(request, 'purchasing/gr_form.html', {
        'page_title': f'Goods Receipt — {po.number}',
        'form': form, 'po': po, 'pending_items': pending_items,
    })


@login_required
@require_company
def gr_detail(request, uid):
    gr = get_object_or_404(GoodsReceipt, uid=uid, company=request.company)
    items = gr.items.select_related('po_item__product', 'po_item__unit')
    return render(request, 'purchasing/gr_detail.html', {
        'page_title': gr.number, 'gr': gr, 'items': items,
    })


@login_required
@require_company
@require_POST
def gr_confirm(request, uid):
    gr = get_object_or_404(GoodsReceipt, uid=uid, company=request.company)
    try:
        gr.confirm(request.user)
        messages.success(request, f'GR {gr.number} dikonfirmasi. Stok telah diupdate.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('purchasing:gr_detail', uid=gr.uid)
