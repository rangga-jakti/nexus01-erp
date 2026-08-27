"""finance/exports.py"""
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
def export_invoice_excel(request):
    from finance.models import Invoice
    company = request.company
    inv_type = request.GET.get('type', '')
    qs = Invoice.objects.filter(company=company).select_related('supplier', 'customer')
    if inv_type:
        qs = qs.filter(invoice_type=inv_type)
    qs = qs.order_by('-invoice_date')

    exp = ExcelExporter("Laporan Invoice", company.name)
    headers = ['Nomor', 'Tipe', 'Pihak', 'Tanggal', 'Jatuh Tempo',
               'Subtotal', 'Pajak', 'Total', 'Dibayar', 'Sisa', 'Status']
    rows = []
    for inv in qs:
        pihak = inv.customer.name if inv.customer else (inv.supplier.name if inv.supplier else '')
        rows.append([
            inv.number,
            inv.get_invoice_type_display(),
            pihak,
            inv.invoice_date.strftime('%d/%m/%Y'),
            inv.due_date.strftime('%d/%m/%Y') if inv.due_date else '',
            float(inv.subtotal),
            float(inv.tax_amount),
            float(inv.total_amount),
            float(inv.paid_amount),
            float(inv.outstanding_amount),
            inv.get_status_display(),
        ])
    exp.add_sheet("Invoice", headers, rows,
                  [16, 14, 24, 12, 12, 14, 12, 14, 14, 14, 12])
    return exp.response(f"invoice_{company.code}.xlsx")


@login_required
@require_company
def export_invoice_pdf(request, uid):
    """Export satu invoice sebagai PDF."""
    from finance.models import Invoice
    invoice = get_object_or_404(Invoice, uid=uid, company=request.company)
    payments = invoice.payments.filter(status='CONFIRMED')

    pdf = PDFExporter(f"Invoice {invoice.number}", request.company)
    pdf.build_header()

    pihak = invoice.customer.name if invoice.customer else (
        invoice.supplier.name if invoice.supplier else '—')
    pdf.add_info_grid([
        ("No. Invoice", invoice.number),
        ("Tanggal", invoice.invoice_date.strftime('%d %B %Y')),
        ("Kepada / Dari", pihak),
        ("Jatuh Tempo", invoice.due_date.strftime('%d %B %Y') if invoice.due_date else '—'),
        ("Tipe", invoice.get_invoice_type_display()),
        ("Status", invoice.get_status_display()),
    ])

    # Ringkasan nilai
    pdf.add_table(
        ['Keterangan', 'Nilai'],
        [
            ['Subtotal', f"Rp {invoice.subtotal:,.0f}"],
            ['Pajak', f"Rp {invoice.tax_amount:,.0f}"],
            ['Diskon', f"Rp {invoice.discount_amount:,.0f}"],
            ['TOTAL', f"Rp {invoice.total_amount:,.0f}"],
            ['Sudah Dibayar', f"Rp {invoice.paid_amount:,.0f}"],
            ['SISA TAGIHAN', f"Rp {invoice.outstanding_amount:,.0f}"],
        ],
        [12, 6],
        "Rincian Tagihan"
    )

    # Riwayat pembayaran
    if payments.exists():
        pay_rows = [[
            p.number,
            p.payment_date.strftime('%d/%m/%Y'),
            p.get_payment_method_display(),
            p.reference_number or '—',
            f"Rp {p.amount:,.0f}",
        ] for p in payments]
        pdf.add_table(
            ['No. Payment', 'Tanggal', 'Metode', 'Referensi', 'Jumlah'],
            pay_rows,
            [3.5, 2.5, 3, 3.5, 3.5],
            "Riwayat Pembayaran"
        )

    return pdf.response(f"Invoice_{invoice.number.replace('/', '-')}.pdf")


@login_required
@require_company
def export_expense_excel(request):
    from finance.models import Expense
    company = request.company
    qs = Expense.objects.filter(company=company).order_by('-expense_date')

    exp = ExcelExporter("Laporan Expense", company.name)
    headers = ['Nomor', 'Judul', 'Kategori', 'Jumlah', 'Status', 'Tanggal', 'Departemen']
    rows = []
    for e in qs:
        rows.append([
            e.number, e.title, e.get_category_display(),
            float(e.amount), e.get_status_display(),
            e.expense_date.strftime('%d/%m/%Y'),
            e.department.name if e.department else '',
        ])
    exp.add_sheet("Expense", headers, rows, [14, 30, 20, 14, 14, 12, 18])
    return exp.response(f"expense_{company.code}.xlsx")


@login_required
@require_company
def export_payment_excel(request):
    from finance.models import Payment
    company = request.company
    qs = Payment.objects.filter(company=company).select_related('invoice').order_by('-payment_date')

    exp = ExcelExporter("Laporan Payment", company.name)
    headers = ['Nomor', 'Invoice', 'Jumlah', 'Metode', 'Referensi', 'Status', 'Tanggal']
    rows = []
    for p in qs:
        rows.append([
            p.number, p.invoice.number, float(p.amount),
            p.get_payment_method_display(), p.reference_number or '',
            p.get_status_display(), p.payment_date.strftime('%d/%m/%Y'),
        ])
    exp.add_sheet("Payment", headers, rows, [16, 16, 14, 16, 16, 12, 12])
    return exp.response(f"payment_{company.code}.xlsx")
