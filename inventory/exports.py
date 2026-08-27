"""inventory/exports.py — Export stok dan mutasi ke Excel/PDF"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from core.exports import ExcelExporter, PDFExporter


def require_company(view_func):
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.company:
            return redirect('core:select_company')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
@require_company
def export_stock_excel(request):
    from inventory.models import Stock
    from django.db.models import F

    company = request.company
    stocks = Stock.objects.filter(
        company=company, is_active=True
    ).select_related('product', 'product__category', 'product__unit', 'warehouse')

    exp = ExcelExporter(f"Laporan Stok — {company.name}", company.name)
    headers = ['SKU', 'Nama Produk', 'Kategori', 'Satuan', 'Gudang',
               'Stok Total', 'Reserved', 'Tersedia', 'Harga Beli', 'Nilai Stok']
    rows = []
    for s in stocks:
        nilai = float(s.quantity) * float(s.product.purchase_price)
        rows.append([
            s.product.sku,
            s.product.name,
            s.product.category.name if s.product.category else '',
            s.product.unit.symbol if s.product.unit else '',
            s.warehouse.name,
            float(s.quantity),
            float(s.reserved_quantity),
            float(s.available_quantity),
            float(s.product.purchase_price),
            nilai,
        ])
    col_widths = [14, 30, 18, 10, 18, 12, 12, 12, 14, 16]
    exp.add_sheet("Posisi Stok", headers, rows, col_widths)
    return exp.response(f"stok_{company.code}.xlsx")


@login_required
@require_company
def export_stock_pdf(request):
    from inventory.models import Stock

    company = request.company
    stocks = Stock.objects.filter(
        company=company, is_active=True
    ).select_related('product', 'product__category', 'product__unit', 'warehouse')

    pdf = PDFExporter(f"Laporan Stok", company, landscape=True)
    pdf.build_header()
    pdf.add_info_grid([
        ("Perusahaan", company.name),
        ("Kode", company.code),
        ("Total SKU", stocks.count()),
        ("Tanggal", ""),
    ])

    headers = ['SKU', 'Produk', 'Gudang', 'Stok', 'Reserved', 'Tersedia', 'Harga Beli', 'Nilai Stok']
    rows = []
    total_nilai = 0
    for s in stocks:
        nilai = float(s.quantity) * float(s.product.purchase_price)
        total_nilai += nilai
        rows.append([
            s.product.sku, s.product.name, s.warehouse.name,
            f"{s.quantity:,.2f}", f"{s.reserved_quantity:,.2f}",
            f"{s.available_quantity:,.2f}",
            f"Rp {s.product.purchase_price:,.0f}",
            f"Rp {nilai:,.0f}",
        ])
    col_widths = [2.5, 5.5, 4, 2.5, 2.5, 2.5, 3.5, 4]
    pdf.add_table(headers, rows, col_widths)
    pdf.add_summary([
        ("Total Nilai Stok", f"Rp {total_nilai:,.0f}"),
    ])
    return pdf.response(f"stok_{company.code}.pdf")


@login_required
@require_company
def export_movement_excel(request):
    from inventory.models import StockMovement

    company = request.company
    date_from = request.GET.get('from', '')
    date_to = request.GET.get('to', '')

    qs = StockMovement.objects.filter(company=company).select_related(
        'product', 'warehouse', 'created_by'
    ).order_by('-created_at')

    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    exp = ExcelExporter(f"Mutasi Stok — {company.name}", company.name)
    headers = ['Tanggal', 'SKU', 'Produk', 'Gudang', 'Tipe', 'Qty', 'Saldo Sebelum', 'Saldo Sesudah', 'Referensi', 'Dicatat oleh']
    rows = []
    for m in qs:
        rows.append([
            m.created_at.strftime('%d/%m/%Y %H:%M'),
            m.product.sku,
            m.product.name,
            m.warehouse.code,
            m.get_movement_type_display(),
            float(m.quantity),
            float(m.quantity_before),
            float(m.quantity_after),
            m.reference or '',
            m.created_by.get_full_name() if m.created_by else '',
        ])
    col_widths = [16, 12, 28, 10, 20, 10, 14, 14, 14, 18]
    exp.add_sheet("Mutasi Stok", headers, rows, col_widths)
    return exp.response(f"mutasi_stok_{company.code}.xlsx")
