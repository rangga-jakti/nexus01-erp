"""sales/exports.py"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404
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
def export_so_excel(request):
    from sales.models import SalesOrder
    company = request.company
    qs = SalesOrder.objects.filter(company=company).select_related('customer').order_by('-created_at')

    exp = ExcelExporter("Laporan Sales Order", company.name)

    # Sheet 1: Summary
    headers = ['Nomor SO', 'Customer', 'Status', 'Tanggal Order', 'Total', 'PPN', 'Grand Total']
    rows = []
    for so in qs:
        rows.append([
            so.number, so.customer.name, so.get_status_display(),
            so.order_date.strftime('%d/%m/%Y'),
            float(so.subtotal),
            float(so.subtotal * so.tax_rate / 100),
            float(so.total_amount),
        ])
    exp.add_sheet("Summary SO", headers, rows, [14, 24, 14, 12, 14, 12, 14])

    # Sheet 2: Detail items
    headers2 = ['Nomor SO', 'Customer', 'Produk', 'SKU', 'Qty', 'Dikirim', 'Sisa', 'Harga', 'Subtotal']
    rows2 = []
    for so in qs:
        for item in so.items.select_related('product'):
            rows2.append([
                so.number, so.customer.name, item.product.name,
                item.product.sku, float(item.quantity),
                float(item.quantity_delivered), float(item.quantity_pending),
                float(item.unit_price), float(item.subtotal),
            ])
    exp.add_sheet("Detail Item SO", headers2, rows2,
                  [14, 20, 26, 12, 10, 10, 10, 14, 14])

    return exp.response(f"sales_order_{company.code}.xlsx")


@login_required
@require_company
def export_so_pdf(request, so_uid):
    """Export satu SO sebagai PDF."""
    from sales.models import SalesOrder
    so = get_object_or_404(SalesOrder, uid=so_uid, company=request.company)
    items = so.items.select_related('product', 'unit')

    pdf = PDFExporter(f"Sales Order {so.number}", request.company)
    pdf.build_header()
    pdf.add_info_grid([
        ("No. SO", so.number),
        ("Tanggal", so.order_date.strftime('%d %B %Y')),
        ("Customer", so.customer.name),
        ("Expected Delivery", so.expected_delivery_date.strftime('%d %B %Y') if so.expected_delivery_date else '—'),
        ("Kontak", so.customer.phone or '—'),
        ("Status", so.get_status_display()),
    ])

    headers = ['No', 'SKU', 'Produk', 'Qty', 'Satuan', 'Harga', 'Subtotal']
    rows = []
    for i, item in enumerate(items, 1):
        rows.append([
            str(i), item.product.sku, item.product.name,
            f"{item.quantity:,.2f}",
            item.unit.symbol if item.unit else '',
            f"Rp {item.unit_price:,.0f}",
            f"Rp {item.subtotal:,.0f}",
        ])
    col_widths = [0.8, 2.5, 7, 2, 1.5, 3, 3.5]
    pdf.add_table(headers, rows, col_widths, "Daftar Item")
    pdf.add_summary([
        ("Subtotal", f"Rp {so.subtotal:,.0f}"),
        (f"PPN {so.tax_rate}%", f"Rp {so.subtotal * so.tax_rate / 100:,.0f}"),
        ("TOTAL", f"Rp {so.total_amount:,.0f}"),
    ])
    return pdf.response(f"SO_{so.number.replace('/', '-')}.pdf")


@login_required
@require_company
def export_customer_excel(request):
    from sales.models import Customer
    company = request.company
    qs = Customer.objects.filter(company=company, is_active=True).order_by('name')

    exp = ExcelExporter("Data Customer", company.name)
    headers = ['Kode', 'Nama', 'Kontak', 'Email', 'Telepon', 'Kota', 'NPWP', 'Term Bayar', 'Credit Limit']
    rows = [[c.code, c.name, c.contact_person, c.email, c.phone,
             c.city, c.tax_id, c.payment_terms_days, float(c.credit_limit)]
            for c in qs]
    exp.add_sheet("Customer", headers, rows, [10, 28, 20, 24, 14, 14, 16, 10, 14])
    return exp.response(f"customer_{company.code}.xlsx")
