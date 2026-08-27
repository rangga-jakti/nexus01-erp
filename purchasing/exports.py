"""purchasing/exports.py"""
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
def export_pr_excel(request):
    from purchasing.models import PurchaseRequest
    company = request.company
    qs = PurchaseRequest.objects.filter(company=company).select_related(
        'created_by', 'department', 'suggested_supplier'
    ).order_by('-created_at')

    exp = ExcelExporter(f"Laporan Purchase Request", company.name)
    headers = ['Nomor', 'Judul', 'Status', 'Dibuat oleh', 'Departemen',
               'Supplier Saran', 'Est. Total', 'Tanggal Submit', 'Tanggal Approved']
    rows = []
    for pr in qs:
        rows.append([
            pr.number, pr.title, pr.get_status_display(),
            pr.created_by.get_full_name() if pr.created_by else '',
            pr.department.name if pr.department else '',
            pr.suggested_supplier.name if pr.suggested_supplier else '',
            float(pr.total_amount),
            pr.submitted_at.strftime('%d/%m/%Y') if pr.submitted_at else '',
            pr.approved_at.strftime('%d/%m/%Y') if pr.approved_at else '',
        ])
    exp.add_sheet("Purchase Request", headers, rows,
                  [14, 30, 16, 18, 16, 20, 14, 14, 14])
    return exp.response(f"purchase_request_{company.code}.xlsx")


@login_required
@require_company
def export_po_excel(request):
    from purchasing.models import PurchaseOrder, PurchaseOrderItem
    company = request.company
    qs = PurchaseOrder.objects.filter(company=company).select_related('supplier').order_by('-created_at')

    exp = ExcelExporter(f"Laporan Purchase Order", company.name)

    # Sheet 1: Summary PO
    headers_po = ['Nomor PO', 'Supplier', 'Status', 'Tanggal Order',
                  'Expected', 'Subtotal', 'PPN', 'Total', 'Payment Terms']
    rows_po = []
    for po in qs:
        rows_po.append([
            po.number, po.supplier.name, po.get_status_display(),
            po.order_date.strftime('%d/%m/%Y'),
            po.expected_date.strftime('%d/%m/%Y') if po.expected_date else '',
            float(po.subtotal), float(po.tax_amount), float(po.total_amount),
            po.payment_terms or '',
        ])
    exp.add_sheet("Summary PO", headers_po, rows_po,
                  [14, 24, 14, 12, 12, 14, 14, 14, 12])

    # Sheet 2: Detail items
    headers_item = ['Nomor PO', 'Supplier', 'SKU', 'Produk',
                    'Qty Order', 'Qty Diterima', 'Sisa', 'Harga Satuan', 'Subtotal']
    rows_item = []
    for po in qs:
        for item in po.items.select_related('product'):
            rows_item.append([
                po.number, po.supplier.name,
                item.product.sku, item.product.name,
                float(item.quantity), float(item.quantity_received),
                float(item.quantity_pending),
                float(item.unit_price), float(item.subtotal),
            ])
    exp.add_sheet("Detail Item PO", headers_item, rows_item,
                  [14, 20, 12, 26, 10, 12, 10, 14, 14])

    return exp.response(f"purchase_order_{company.code}.xlsx")


@login_required
@require_company
def export_po_pdf(request, po_uid):
    """Export satu PO sebagai PDF — untuk dikirim ke supplier."""
    from purchasing.models import PurchaseOrder
    from django.shortcuts import get_object_or_404

    po = get_object_or_404(PurchaseOrder, uid=po_uid, company=request.company)
    items = po.items.select_related('product', 'unit')

    pdf = PDFExporter(f"Purchase Order {po.number}", request.company, landscape=False)
    pdf.build_header()

    pdf.add_info_grid([
        ("No. PO", po.number),
        ("Tanggal", po.order_date.strftime('%d %B %Y')),
        ("Supplier", po.supplier.name),
        ("Expected", po.expected_date.strftime('%d %B %Y') if po.expected_date else '—'),
        ("Payment Terms", po.payment_terms or '—'),
        ("Status", po.get_status_display()),
        ("Gudang Tujuan", po.warehouse.name if po.warehouse else '—'),
        ("Ref Supplier", po.supplier_reference or '—'),
    ])

    headers = ['No', 'SKU', 'Nama Produk', 'Qty', 'Satuan', 'Harga', 'Subtotal']
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
        ("Subtotal", f"Rp {po.subtotal:,.0f}"),
        (f"PPN {po.tax_rate}%", f"Rp {po.tax_amount:,.0f}"),
        ("TOTAL", f"Rp {po.total_amount:,.0f}"),
    ])
    return pdf.response(f"PO_{po.number.replace('/', '-')}.pdf")
