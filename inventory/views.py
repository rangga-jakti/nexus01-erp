"""
inventory/views.py

Semua view inventory — Product, Warehouse, Stock, StockMovement.

Pattern yang dipakai konsisten di semua view:
- List view: queryset + filter + paginate, support HTMX partial reload
- Detail view: object + related data
- Create/Edit: ModelForm dengan validasi
- HTMX endpoints: prefix htmx_ untuk partial responses
"""

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST, require_GET
from django.core.paginator import Paginator
from django.db.models import Q, Sum, F, Count
from django.http import HttpResponse
from django.utils import timezone

from .models import Product, ProductCategory, UnitOfMeasure, Warehouse, Stock, StockMovement
from .forms import ProductForm, WarehouseForm, StockAdjustmentForm, ProductCategoryForm, UOMForm


def require_company(view_func):
    """Decorator: redirect ke select_company jika belum ada active company."""
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.company:
            messages.warning(request, 'Pilih perusahaan terlebih dahulu.')
            return redirect('core:select_company')
        return view_func(request, *args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# PRODUCT
# ---------------------------------------------------------------------------

@login_required
@require_company
def product_list(request):
    company = request.company
    q = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '')
    product_type = request.GET.get('type', '')
    stock_filter = request.GET.get('stock', '')

    qs = Product.objects.filter(company=company, is_active=True).select_related(
        'category', 'unit'
    ).prefetch_related('stocks')

    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(barcode__icontains=q))
    if category_id:
        qs = qs.filter(category_id=category_id)
    if product_type:
        qs = qs.filter(product_type=product_type)

    # Annotate total stock
    qs = qs.annotate(stock_total=Sum('stocks__quantity'))

    if stock_filter == 'low':
        # Produk dengan stok <= minimum_stock
        qs = qs.filter(stock_total__lte=F('minimum_stock'))
    elif stock_filter == 'zero':
        qs = qs.filter(Q(stock_total__isnull=True) | Q(stock_total=0))

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page', 1))

    categories = ProductCategory.objects.filter(company=company, is_active=True)

    context = {
        'page_title': 'Produk',
        'products': page,
        'categories': categories,
        'product_types': Product.ProductType.choices,
        'q': q,
        'selected_category': category_id,
        'selected_type': product_type,
        'selected_stock': stock_filter,
        'total_count': qs.count(),
        # Stats
        'stats': {
            'total': Product.objects.filter(company=company, is_active=True).count(),
            'low_stock': Product.objects.filter(company=company, is_active=True)
                .annotate(st=Sum('stocks__quantity'))
                .filter(st__lte=F('minimum_stock'), product_type='STORABLE').count(),
            'zero_stock': Product.objects.filter(company=company, is_active=True)
                .annotate(st=Sum('stocks__quantity'))
                .filter(Q(st__isnull=True) | Q(st=0)).count(),
        }
    }

    # HTMX: hanya return table partial, bukan full page
    if request.htmx:
        return render(request, 'inventory/partials/product_table.html', context)

    return render(request, 'inventory/product_list.html', context)


@login_required
@require_company
def product_detail(request, uid):
    product = get_object_or_404(Product, uid=uid, company=request.company)
    stocks = Stock.objects.filter(
        product=product, is_active=True
    ).select_related('warehouse').order_by('warehouse__name')

    movements = StockMovement.objects.filter(
        product=product, company=request.company
    ).select_related('warehouse', 'created_by').order_by('-created_at')[:30]

    context = {
        'page_title': product.name,
        'product': product,
        'stocks': stocks,
        'movements': movements,
        'total_stock': product.total_stock,
    }
    return render(request, 'inventory/product_detail.html', context)


@login_required
@require_company
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, company=request.company)
        if form.is_valid():
            product = form.save(commit=False)
            product.company = request.company
            product.created_by = request.user
            product.save()
            from core.models import AuditLog
            AuditLog.log(user=request.user, action=AuditLog.Action.CREATE,
                        obj=product, company=request.company,
                        message=f'Produk {product.sku} dibuat')
            messages.success(request, f'Produk "{product.name}" berhasil dibuat.')
            return redirect('inventory:product_detail', uid=product.uid)
    else:
        form = ProductForm(company=request.company)

    return render(request, 'inventory/product_form.html', {
        'page_title': 'Tambah Produk',
        'form': form,
        'action': 'create',
    })


@login_required
@require_company
def product_edit(request, uid):
    product = get_object_or_404(Product, uid=uid, company=request.company)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product, company=request.company)
        if form.is_valid():
            product = form.save(commit=False)
            product.updated_by = request.user
            product.save()
            from core.models import AuditLog
            AuditLog.log(user=request.user, action=AuditLog.Action.UPDATE,
                        obj=product, company=request.company)
            messages.success(request, f'Produk "{product.name}" berhasil diupdate.')
            return redirect('inventory:product_detail', uid=product.uid)
    else:
        form = ProductForm(instance=product, company=request.company)

    return render(request, 'inventory/product_form.html', {
        'page_title': f'Edit: {product.name}',
        'form': form,
        'product': product,
        'action': 'edit',
    })


@login_required
@require_company
@require_POST
def product_delete(request, uid):
    product = get_object_or_404(Product, uid=uid, company=request.company)
    product.soft_delete(user=request.user)
    from core.models import AuditLog
    AuditLog.log(user=request.user, action=AuditLog.Action.DELETE,
                obj=product, company=request.company)
    messages.success(request, f'Produk "{product.name}" dihapus.')
    return redirect('inventory:product_list')


# ---------------------------------------------------------------------------
# WAREHOUSE
# ---------------------------------------------------------------------------

@login_required
@require_company
def warehouse_list(request):
    warehouses = Warehouse.objects.filter(
        company=request.company, is_active=True
    ).select_related('branch').annotate(
        product_count=Count('stocks__product', distinct=True),
        total_stock_value=Sum(
            F('stocks__quantity') * F('stocks__product__purchase_price')
        )
    ).order_by('name')

    return render(request, 'inventory/warehouse_list.html', {
        'page_title': 'Gudang',
        'warehouses': warehouses,
    })


@login_required
@require_company
def warehouse_detail(request, uid):
    warehouse = get_object_or_404(Warehouse, uid=uid, company=request.company)
    q = request.GET.get('q', '').strip()

    stocks = Stock.objects.filter(
        warehouse=warehouse, is_active=True
    ).select_related('product', 'product__category', 'product__unit')

    if q:
        stocks = stocks.filter(
            Q(product__name__icontains=q) | Q(product__sku__icontains=q)
        )

    stocks = stocks.order_by('product__name')
    paginator = Paginator(stocks, 30)
    page = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'inventory/warehouse_detail.html', {
        'page_title': warehouse.name,
        'warehouse': warehouse,
        'stocks': page,
        'q': q,
        'total_items': stocks.count(),
    })


@login_required
@require_company
def warehouse_create(request):
    if request.method == 'POST':
        form = WarehouseForm(request.POST, company=request.company)
        if form.is_valid():
            wh = form.save(commit=False)
            wh.company = request.company
            wh.created_by = request.user
            wh.save()
            messages.success(request, f'Gudang "{wh.name}" berhasil dibuat.')
            return redirect('inventory:warehouse_list')
    else:
        form = WarehouseForm(company=request.company)

    return render(request, 'inventory/warehouse_form.html', {
        'page_title': 'Tambah Gudang',
        'form': form,
    })


@login_required
@require_company
def warehouse_edit(request, uid):
    warehouse = get_object_or_404(Warehouse, uid=uid, company=request.company)
    if request.method == 'POST':
        form = WarehouseForm(request.POST, instance=warehouse, company=request.company)
        if form.is_valid():
            form.save()
            messages.success(request, f'Gudang "{warehouse.name}" diupdate.')
            return redirect('inventory:warehouse_list')
    else:
        form = WarehouseForm(instance=warehouse, company=request.company)

    return render(request, 'inventory/warehouse_form.html', {
        'page_title': f'Edit Gudang: {warehouse.name}',
        'form': form,
        'warehouse': warehouse,
    })


# ---------------------------------------------------------------------------
# STOCK
# ---------------------------------------------------------------------------

@login_required
@require_company
def stock_list(request):
    company = request.company
    q = request.GET.get('q', '').strip()
    warehouse_id = request.GET.get('warehouse', '')
    alert_only = request.GET.get('alert', '')

    qs = Stock.objects.filter(
        company=company, is_active=True
    ).select_related(
        'product', 'product__category', 'product__unit', 'warehouse'
    )

    if q:
        qs = qs.filter(
            Q(product__name__icontains=q) | Q(product__sku__icontains=q)
        )
    if warehouse_id:
        qs = qs.filter(warehouse_id=warehouse_id)
    if alert_only:
        qs = qs.filter(quantity__lte=F('product__minimum_stock'))

    qs = qs.order_by('product__name', 'warehouse__name')
    paginator = Paginator(qs, 30)
    page = paginator.get_page(request.GET.get('page', 1))

    warehouses = Warehouse.objects.filter(company=company, is_active=True)

    context = {
        'page_title': 'Stok',
        'stocks': page,
        'warehouses': warehouses,
        'q': q,
        'selected_warehouse': warehouse_id,
        'alert_only': alert_only,
        'low_stock_count': Stock.objects.filter(
            company=company,
            quantity__lte=F('product__minimum_stock'),
            product__product_type='STORABLE',
        ).count(),
    }

    if request.htmx:
        return render(request, 'inventory/partials/stock_table.html', context)
    return render(request, 'inventory/stock_list.html', context)


@login_required
@require_company
def stock_adjust(request, stock_id):
    """Stock adjustment manual — tambah atau kurangi stok dengan alasan."""
    stock = get_object_or_404(Stock, pk=stock_id, company=request.company)

    if request.method == 'POST':
        form = StockAdjustmentForm(request.POST)
        if form.is_valid():
            qty = form.cleaned_data['quantity']
            adj_type = form.cleaned_data['adjustment_type']
            notes = form.cleaned_data['notes']

            try:
                if adj_type == 'add':
                    stock.add_stock(
                        qty=qty,
                        movement_type=StockMovement.MovementType.ADJUSTMENT_IN,
                        notes=notes,
                        user=request.user,
                    )
                    msg = f'Stok ditambah {qty} {stock.product.unit or "unit"}'
                else:
                    stock.reduce_stock(
                        qty=qty,
                        movement_type=StockMovement.MovementType.ADJUSTMENT_OUT,
                        notes=notes,
                        user=request.user,
                    )
                    msg = f'Stok dikurangi {qty} {stock.product.unit or "unit"}'

                messages.success(request, msg)
                return redirect('inventory:stock_list')
            except ValueError as e:
                messages.error(request, str(e))
    else:
        form = StockAdjustmentForm()

    return render(request, 'inventory/stock_adjust.html', {
        'page_title': f'Adjust Stok: {stock.product.name}',
        'stock': stock,
        'form': form,
    })


# ---------------------------------------------------------------------------
# STOCK MOVEMENT
# ---------------------------------------------------------------------------

@login_required
@require_company
def movement_list(request):
    company = request.company
    q = request.GET.get('q', '').strip()
    movement_type = request.GET.get('type', '')
    warehouse_id = request.GET.get('warehouse', '')
    date_from = request.GET.get('from', '')
    date_to = request.GET.get('to', '')

    qs = StockMovement.objects.filter(
        company=company
    ).select_related('product', 'warehouse', 'created_by').order_by('-created_at')

    if q:
        qs = qs.filter(
            Q(product__name__icontains=q) | Q(product__sku__icontains=q) | Q(reference__icontains=q)
        )
    if movement_type:
        qs = qs.filter(movement_type=movement_type)
    if warehouse_id:
        qs = qs.filter(warehouse_id=warehouse_id)
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    paginator = Paginator(qs, 40)
    page = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'inventory/movement_list.html', {
        'page_title': 'Mutasi Stok',
        'movements': page,
        'movement_types': StockMovement.MovementType.choices,
        'warehouses': Warehouse.objects.filter(company=company, is_active=True),
        'q': q,
        'selected_type': movement_type,
        'selected_warehouse': warehouse_id,
        'date_from': date_from,
        'date_to': date_to,
    })


# ---------------------------------------------------------------------------
# HTMX endpoints
# ---------------------------------------------------------------------------

@login_required
@require_company
@require_GET
def htmx_product_search(request):
    """Live search untuk dropdown product (dipakai di form PR, PO, dll)."""
    q = request.GET.get('q', '').strip()
    products = []
    if q and len(q) >= 2:
        products = Product.objects.filter(
            company=request.company,
            is_active=True,
            product_type='STORABLE',
        ).filter(
            Q(name__icontains=q) | Q(sku__icontains=q)
        ).select_related('unit')[:10]

    return render(request, 'inventory/partials/product_search_results.html', {
        'products': products,
        'q': q,
    })


@login_required
@require_company
@require_GET
def htmx_stock_badge(request, product_id):
    """Return badge stok terkini untuk product tertentu (realtime update)."""
    try:
        product = Product.objects.get(pk=product_id, company=request.company)
        total = product.total_stock
    except Product.DoesNotExist:
        total = 0
    return render(request, 'inventory/partials/stock_badge.html', {'total': total})
