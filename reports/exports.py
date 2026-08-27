"""reports/exports.py — Export laporan rekap dari semua modul"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from core.exports import ExcelExporter, PDFExporter
from datetime import datetime, timedelta


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
def export_full_report_excel(request):
    """Export laporan lengkap semua modul dalam satu file Excel multi-sheet."""
    from django.db.models import Sum, Count, F, Q
    from django.utils import timezone

    company = request.company
    today = timezone.now().date()
    month_start = today.replace(day=1)

    exp = ExcelExporter(f"Laporan Lengkap — {company.name}", company.name)

    # ── Sheet 1: Summary Eksekutif ─────────────────────────────────────────
    try:
        from inventory.models import Stock, Product
        from purchasing.models import PurchaseOrder, PurchaseRequest
        from sales.models import SalesOrder
        from finance.models import Invoice, Payment, Expense

        stock_value = Stock.objects.filter(company=company, is_active=True).aggregate(
            v=Sum(F('quantity') * F('product__purchase_price'))
        )['v'] or 0

        so_month = SalesOrder.objects.filter(
            company=company, created_at__date__gte=month_start
        ).aggregate(v=Sum(F('items__quantity') * F('items__unit_price')))['v'] or 0

        receivable = Invoice.objects.filter(
            company=company, invoice_type='SALES',
            status__in=['ISSUED', 'PARTIAL', 'OVERDUE']
        ).aggregate(v=Sum('subtotal'))['v'] or 0

        payable = Invoice.objects.filter(
            company=company, invoice_type='PURCHASE',
            status__in=['ISSUED', 'PARTIAL', 'OVERDUE']
        ).aggregate(v=Sum('subtotal'))['v'] or 0

        exp_month = Expense.objects.filter(
            company=company, expense_date__gte=month_start
        ).aggregate(v=Sum('amount'))['v'] or 0

        summary_headers = ['Indikator', 'Nilai', 'Keterangan']
        summary_rows = [
            ['Nilai Total Stok', float(stock_value), 'Qty × Harga Beli'],
            ['Total Produk Aktif', Product.objects.filter(company=company, is_active=True).count(), 'SKU'],
            ['Sales Bulan Ini', float(so_month), 'Dari Sales Order confirmed'],
            ['SO Bulan Ini', SalesOrder.objects.filter(company=company, created_at__date__gte=month_start).count(), 'Jumlah transaksi'],
            ['Piutang Outstanding', float(receivable), 'Invoice penjualan belum lunas'],
            ['Hutang Outstanding', float(payable), 'Invoice pembelian belum lunas'],
            ['Net Position', float(receivable - payable), 'Piutang - Hutang'],
            ['Expense Bulan Ini', float(exp_month), 'Total pengeluaran operasional'],
            ['PR Pending', PurchaseRequest.objects.filter(company=company, status='PENDING').count(), 'Menunggu approval'],
            ['Invoice Overdue', Invoice.objects.filter(company=company, due_date__lt=today, status__in=['ISSUED', 'PARTIAL']).count(), 'Melewati jatuh tempo'],
        ]
        exp.add_sheet("Executive Summary", summary_headers, summary_rows, [30, 18, 30])
    except Exception as e:
        exp.add_sheet("Executive Summary", ['Error'], [[str(e)]])

    # ── Sheet 2: Stok per Gudang ───────────────────────────────────────────
    try:
        from inventory.models import Stock
        stocks = Stock.objects.filter(
            company=company, is_active=True
        ).select_related('product', 'product__category', 'product__unit', 'warehouse')

        headers = ['SKU', 'Produk', 'Kategori', 'Gudang', 'Stok', 'Reserved', 'Tersedia', 'Min Stok', 'Status', 'Nilai']
        rows = []
        for s in stocks:
            if s.quantity == 0:
                status = 'KOSONG'
            elif s.product.minimum_stock > 0 and s.quantity <= s.product.minimum_stock:
                status = 'RENDAH'
            else:
                status = 'AMAN'
            rows.append([
                s.product.sku, s.product.name,
                s.product.category.name if s.product.category else '',
                s.warehouse.name, float(s.quantity),
                float(s.reserved_quantity), float(s.available_quantity),
                float(s.product.minimum_stock), status,
                float(s.quantity) * float(s.product.purchase_price),
            ])
        exp.add_sheet("Posisi Stok", headers, rows,
                      [12, 28, 16, 16, 10, 10, 10, 10, 8, 14])
    except Exception:
        pass

    # ── Sheet 3: Sales Order bulan ini ────────────────────────────────────
    try:
        from sales.models import SalesOrder
        sos = SalesOrder.objects.filter(
            company=company, created_at__date__gte=month_start
        ).select_related('customer').order_by('-created_at')

        headers = ['Nomor SO', 'Customer', 'Status', 'Tanggal', 'Total']
        rows = [[so.number, so.customer.name, so.get_status_display(),
                 so.order_date.strftime('%d/%m/%Y'), float(so.total_amount)]
                for so in sos]
        exp.add_sheet(f"SO Bulan Ini", headers, rows, [14, 28, 14, 12, 14])
    except Exception:
        pass

    # ── Sheet 4: Invoice & Pembayaran ─────────────────────────────────────
    try:
        from finance.models import Invoice
        invs = Invoice.objects.filter(
            company=company
        ).select_related('customer', 'supplier').order_by('-invoice_date')[:200]

        headers = ['Nomor', 'Tipe', 'Pihak', 'Total', 'Dibayar', 'Sisa', 'Status', 'Jatuh Tempo']
        rows = []
        for inv in invs:
            pihak = inv.customer.name if inv.customer else (inv.supplier.name if inv.supplier else '')
            rows.append([
                inv.number, inv.get_invoice_type_display(), pihak,
                float(inv.total_amount), float(inv.paid_amount),
                float(inv.outstanding_amount), inv.get_status_display(),
                inv.due_date.strftime('%d/%m/%Y') if inv.due_date else '',
            ])
        exp.add_sheet("Invoice", headers, rows, [16, 14, 24, 14, 14, 14, 12, 12])
    except Exception:
        pass

    # ── Sheet 5: Purchase Order ────────────────────────────────────────────
    try:
        from purchasing.models import PurchaseOrder
        pos = PurchaseOrder.objects.filter(
            company=company
        ).select_related('supplier').order_by('-created_at')[:200]

        headers = ['Nomor PO', 'Supplier', 'Status', 'Tanggal', 'Total']
        rows = [[po.number, po.supplier.name, po.get_status_display(),
                 po.order_date.strftime('%d/%m/%Y'), float(po.total_amount)]
                for po in pos]
        exp.add_sheet("Purchase Order", headers, rows, [14, 28, 14, 12, 14])
    except Exception:
        pass

    return exp.response(f"laporan_lengkap_{company.code}_{today.strftime('%Y%m%d')}.xlsx")


@login_required
@require_company
def export_full_report_pdf(request):
    """Export ringkasan eksekutif sebagai PDF."""
    from django.db.models import Sum, F
    from django.utils import timezone

    company = request.company
    today = timezone.now().date()
    month_start = today.replace(day=1)

    pdf = PDFExporter(f"Laporan Eksekutif — {today.strftime('%B %Y')}", company, landscape=False)
    pdf.build_header()

    # Info perusahaan
    pdf.add_info_grid([
        ("Perusahaan", company.name),
        ("Kode", company.code),
        ("Periode", today.strftime('%B %Y')),
        ("Mata Uang", company.currency),
    ])

    # KPI Summary
    try:
        from inventory.models import Stock, Product
        from purchasing.models import PurchaseRequest, PurchaseOrder
        from sales.models import SalesOrder
        from finance.models import Invoice, Expense

        stock_value = Stock.objects.filter(company=company, is_active=True).aggregate(
            v=Sum(F('quantity') * F('product__purchase_price'))
        )['v'] or 0

        so_value = SalesOrder.objects.filter(
            company=company, created_at__date__gte=month_start
        ).aggregate(v=Sum(F('items__quantity') * F('items__unit_price')))['v'] or 0

        receivable = Invoice.objects.filter(
            company=company, invoice_type='SALES', status__in=['ISSUED', 'PARTIAL', 'OVERDUE']
        ).aggregate(v=Sum('subtotal'))['v'] or 0

        payable = Invoice.objects.filter(
            company=company, invoice_type='PURCHASE', status__in=['ISSUED', 'PARTIAL', 'OVERDUE']
        ).aggregate(v=Sum('subtotal'))['v'] or 0

        exp_total = Expense.objects.filter(
            company=company, expense_date__gte=month_start
        ).aggregate(v=Sum('amount'))['v'] or 0

        pdf.add_table(
            ['Indikator', 'Nilai'],
            [
                ['Nilai Total Stok', f"Rp {stock_value:,.0f}"],
                ['Sales Bulan Ini', f"Rp {so_value:,.0f}"],
                ['Piutang Outstanding', f"Rp {receivable:,.0f}"],
                ['Hutang Outstanding', f"Rp {payable:,.0f}"],
                ['Net Position (Piutang - Hutang)', f"Rp {receivable - payable:,.0f}"],
                ['Expense Bulan Ini', f"Rp {exp_total:,.0f}"],
                ['PR Pending Approval', str(PurchaseRequest.objects.filter(company=company, status='PENDING').count())],
                ['Invoice Overdue', str(Invoice.objects.filter(company=company, due_date__lt=today, status__in=['ISSUED', 'PARTIAL']).count())],
            ],
            [11, 7],
            "KPI Utama"
        )
    except Exception as e:
        pass

    return pdf.response(f"laporan_eksekutif_{company.code}_{today.strftime('%Y%m%d')}.pdf")
