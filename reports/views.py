"""
reports/views.py

Dashboard utama yang menarik data dari semua modul.
Ini halaman yang pertama kali dilihat investor / atasan — harus impresif.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db.models import Sum, Count, F, Q, Avg
from django.db.models.functions import TruncMonth, TruncDate
from django.utils import timezone
import json
from datetime import timedelta, date


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
def overview(request):
    company = request.company
    today = timezone.now().date()
    month_start = today.replace(day=1)
    last_30 = today - timedelta(days=30)
    last_6m = today - timedelta(days=180)

    ctx = {'page_title': 'Reports & Dashboard', 'today': today}

    # ── INVENTORY ──────────────────────────────────────────────────────────────
    try:
        from inventory.models import Product, Stock, StockMovement

        total_products = Product.objects.filter(company=company, is_active=True).count()
        total_sku_storable = Product.objects.filter(company=company, is_active=True, product_type='STORABLE').count()

        # Nilai total stok (qty × harga beli)
        stock_value = Stock.objects.filter(company=company, is_active=True).aggregate(
            val=Sum(F('quantity') * F('product__purchase_price'))
        )['val'] or 0

        low_stock_items = Stock.objects.filter(
            company=company, is_active=True,
            quantity__lte=F('product__minimum_stock'),
            product__product_type='STORABLE',
        ).count()

        zero_stock = Stock.objects.filter(
            company=company, is_active=True, quantity=0
        ).count()

        # Mutasi stok 30 hari terakhir — chart
        movements_30d = (
            StockMovement.objects
            .filter(company=company, created_at__date__gte=last_30)
            .annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(
                masuk=Sum('quantity', filter=Q(quantity__gt=0)),
                keluar=Sum('quantity', filter=Q(quantity__lt=0)),
            )
            .order_by('day')
        )
        # Pad days dengan 0 untuk chart
        days_map = {m['day']: m for m in movements_30d}
        chart_days, chart_masuk, chart_keluar = [], [], []
        for i in range(30):
            d = last_30 + timedelta(days=i)
            chart_days.append(d.strftime('%d/%m'))
            m = days_map.get(d, {})
            chart_masuk.append(float(m.get('masuk') or 0))
            chart_keluar.append(abs(float(m.get('keluar') or 0)))

        ctx['inventory'] = {
            'total_products': total_products,
            'total_sku_storable': total_sku_storable,
            'stock_value': stock_value,
            'low_stock_items': low_stock_items,
            'zero_stock': zero_stock,
            'chart_days': json.dumps(chart_days),
            'chart_masuk': json.dumps(chart_masuk),
            'chart_keluar': json.dumps(chart_keluar),
        }
    except Exception as e:
        ctx['inventory'] = {'error': str(e)}

    # ── PURCHASING ─────────────────────────────────────────────────────────────
    try:
        from purchasing.models import PurchaseRequest, PurchaseOrder, GoodsReceipt

        pr_pending = PurchaseRequest.objects.filter(company=company, status='PENDING').count()
        pr_month = PurchaseRequest.objects.filter(company=company, created_at__date__gte=month_start).count()

        po_this_month = PurchaseOrder.objects.filter(company=company, created_at__date__gte=month_start)
        po_value_month = po_this_month.aggregate(v=Sum(F('items__quantity') * F('items__unit_price')))['v'] or 0
        po_count_month = po_this_month.count()

        # PO per status
        po_by_status = list(
            PurchaseOrder.objects.filter(company=company)
            .values('status')
            .annotate(n=Count('id'))
            .order_by('status')
        )

        ctx['purchasing'] = {
            'pr_pending': pr_pending,
            'pr_month': pr_month,
            'po_value_month': po_value_month,
            'po_count_month': po_count_month,
            'po_by_status': po_by_status,
        }
    except Exception as e:
        ctx['purchasing'] = {'error': str(e)}

    # ── SALES ──────────────────────────────────────────────────────────────────
    try:
        from sales.models import SalesOrder, Quotation

        so_month = SalesOrder.objects.filter(company=company, created_at__date__gte=month_start)
        so_value_month = so_month.aggregate(
            v=Sum(F('items__quantity') * F('items__unit_price'))
        )['v'] or 0
        so_count_month = so_month.count()

        # Sales 6 bulan terakhir — chart
        sales_6m = (
            SalesOrder.objects
            .filter(company=company, created_at__date__gte=last_6m, status__in=['CONFIRMED','PARTIAL','COMPLETED'])
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(total=Sum(F('items__quantity') * F('items__unit_price')))
            .order_by('month')
        )
        sales_months, sales_values = [], []
        for row in sales_6m:
            sales_months.append(row['month'].strftime('%b %Y') if row['month'] else '')
            sales_values.append(float(row['total'] or 0))

        # Top customer bulan ini
        top_customers = (
            SalesOrder.objects
            .filter(company=company, created_at__date__gte=month_start)
            .values('customer__name')
            .annotate(total=Sum(F('items__quantity') * F('items__unit_price')))
            .order_by('-total')[:5]
        )

        quotation_rate = 0
        qt_total = Quotation.objects.filter(company=company).count()
        qt_accepted = Quotation.objects.filter(company=company, status='ACCEPTED').count()
        if qt_total > 0:
            quotation_rate = round(qt_accepted / qt_total * 100, 1)

        ctx['sales'] = {
            'so_value_month': so_value_month,
            'so_count_month': so_count_month,
            'sales_months': json.dumps(sales_months),
            'sales_values': json.dumps(sales_values),
            'top_customers': list(top_customers),
            'quotation_rate': quotation_rate,
        }
    except Exception as e:
        ctx['sales'] = {'error': str(e)}

    # ── FINANCE ────────────────────────────────────────────────────────────────
    try:
        from finance.models import Invoice, Payment, Expense

        # Piutang vs hutang
        receivable = Invoice.objects.filter(
            company=company, invoice_type='SALES', status__in=['ISSUED','PARTIAL','OVERDUE']
        ).aggregate(v=Sum('subtotal'))['v'] or 0

        payable = Invoice.objects.filter(
            company=company, invoice_type='PURCHASE', status__in=['ISSUED','PARTIAL','OVERDUE']
        ).aggregate(v=Sum('subtotal'))['v'] or 0

        overdue_count = Invoice.objects.filter(
            company=company, due_date__lt=today, status__in=['ISSUED','PARTIAL']
        ).count()

        # Payment bulan ini
        paid_month = Payment.objects.filter(
            company=company, payment_date__gte=month_start, status='CONFIRMED'
        ).aggregate(v=Sum('amount'))['v'] or 0

        # Expense per kategori
        expense_by_cat = list(
            Expense.objects.filter(company=company, expense_date__gte=month_start)
            .values('category')
            .annotate(total=Sum('amount'))
            .order_by('-total')
        )
        exp_labels = [e['category'] for e in expense_by_cat]
        exp_values = [float(e['total'] or 0) for e in expense_by_cat]

        ctx['finance'] = {
            'receivable': receivable,
            'payable': payable,
            'overdue_count': overdue_count,
            'paid_month': paid_month,
            'exp_labels': json.dumps(exp_labels),
            'exp_values': json.dumps(exp_values),
            'net_position': receivable - payable,
        }
    except Exception as e:
        ctx['finance'] = {'error': str(e)}

    return render(request, 'reports/overview.html', ctx)
