"""finance/models.py — Invoice, Payment, Expense"""
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from core.models import CompanyBoundModel


class Invoice(CompanyBoundModel):
    class InvoiceType(models.TextChoices):
        PURCHASE = 'PURCHASE', 'Invoice Pembelian'   # Tagihan dari supplier
        SALES = 'SALES', 'Invoice Penjualan'          # Tagihan ke customer

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        ISSUED = 'ISSUED', 'Diterbitkan'
        PARTIAL = 'PARTIAL', 'Sebagian Dibayar'
        PAID = 'PAID', 'Lunas'
        OVERDUE = 'OVERDUE', 'Jatuh Tempo'
        CANCELLED = 'CANCELLED', 'Dibatalkan'

    number = models.CharField(max_length=30, unique=True, blank=True)
    invoice_type = models.CharField(max_length=20, choices=InvoiceType.choices, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)

    # Relasi ke transaksi sumber
    po = models.ForeignKey('purchasing.PurchaseOrder', null=True, blank=True, on_delete=models.SET_NULL, related_name='invoices')
    so = models.ForeignKey('sales.SalesOrder', null=True, blank=True, on_delete=models.SET_NULL, related_name='invoices')

    # Pihak terkait
    supplier = models.ForeignKey('purchasing.Supplier', null=True, blank=True, on_delete=models.SET_NULL)
    customer = models.ForeignKey('sales.Customer', null=True, blank=True, on_delete=models.SET_NULL)

    branch = models.ForeignKey('organization.Branch', null=True, blank=True, on_delete=models.SET_NULL)
    invoice_date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)

    subtotal = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    @property
    def total_amount(self):
        return self.subtotal + self.tax_amount - self.discount_amount

    @property
    def paid_amount(self):
        return self.payments.filter(status='CONFIRMED').aggregate(
            total=models.Sum('amount')
        )['total'] or 0

    @property
    def outstanding_amount(self):
        return max(0, self.total_amount - self.paid_amount)

    @property
    def is_overdue(self):
        return self.due_date and self.due_date < timezone.now().date() and self.status not in ['PAID', 'CANCELLED']

    notes = models.TextField(blank=True)
    supplier_invoice_number = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.number} [{self.get_status_display()}]"

    def save(self, *args, **kwargs):
        if not self.number:
            y, m = timezone.now().year, timezone.now().month
            prefix = 'INV-P' if self.invoice_type == self.InvoiceType.PURCHASE else 'INV-S'
            count = Invoice.objects.filter(company=self.company, created_at__year=y, created_at__month=m).count() + 1
            self.number = f"{prefix}/{y}{m:02d}/{count:04d}"
        super().save(*args, **kwargs)

    def update_status(self):
        """Recalculate status berdasarkan paid_amount."""
        paid = self.paid_amount
        total = self.total_amount
        if paid >= total:
            self.status = self.Status.PAID
        elif paid > 0:
            self.status = self.Status.PARTIAL
        elif self.is_overdue:
            self.status = self.Status.OVERDUE
        self.save(update_fields=['status'])


class Payment(CompanyBoundModel):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        CONFIRMED = 'CONFIRMED', 'Dikonfirmasi'
        CANCELLED = 'CANCELLED', 'Dibatalkan'

    class PaymentMethod(models.TextChoices):
        TRANSFER = 'TRANSFER', 'Transfer Bank'
        CASH = 'CASH', 'Tunai'
        CHEQUE = 'CHEQUE', 'Cek/Giro'
        VIRTUAL_ACCOUNT = 'VIRTUAL_ACCOUNT', 'Virtual Account'
        OTHER = 'OTHER', 'Lainnya'

    number = models.CharField(max_length=30, unique=True, blank=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='payments')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.TRANSFER)

    amount = models.DecimalField(max_digits=18, decimal_places=2, validators=[MinValueValidator(0)])
    payment_date = models.DateField(default=timezone.now)
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    reference_number = models.CharField(max_length=100, blank=True)
    attachment = models.FileField(upload_to='payment_proofs/', null=True, blank=True)
    notes = models.TextField(blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.number} — Rp {self.amount:,.0f}"

    def save(self, *args, **kwargs):
        if not self.number:
            y, m = timezone.now().year, timezone.now().month
            count = Payment.objects.filter(company=self.company, created_at__year=y, created_at__month=m).count() + 1
            self.number = f"PAY/{y}{m:02d}/{count:04d}"
        super().save(*args, **kwargs)

    def confirm(self, user):
        from django.utils import timezone as tz
        self.status = self.Status.CONFIRMED
        self.confirmed_at = tz.now()
        self.save()
        # Update invoice status
        self.invoice.update_status()
        from core.models import AuditLog
        AuditLog.log(user=user, action=AuditLog.Action.APPROVE, obj=self, company=self.company,
                     message=f"Payment {self.number} dikonfirmasi Rp {self.amount:,.0f}")


class Expense(CompanyBoundModel):
    """Pengeluaran operasional yang tidak terkait PO (bensin, ATK, transport, dll)."""
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PENDING = 'PENDING', 'Menunggu Approval'
        APPROVED = 'APPROVED', 'Disetujui'
        REJECTED = 'REJECTED', 'Ditolak'
        PAID = 'PAID', 'Sudah Dibayar'

    class Category(models.TextChoices):
        TRANSPORT = 'TRANSPORT', 'Transport & Perjalanan'
        UTILITIES = 'UTILITIES', 'Utilitas (Listrik, Air, Internet)'
        OFFICE = 'OFFICE', 'Alat Tulis Kantor'
        SALARY = 'SALARY', 'Gaji & Tunjangan'
        MAINTENANCE = 'MAINTENANCE', 'Perawatan & Perbaikan'
        MARKETING = 'MARKETING', 'Marketing & Promosi'
        OTHER = 'OTHER', 'Lainnya'

    number = models.CharField(max_length=30, unique=True, blank=True)
    title = models.CharField(max_length=300)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    branch = models.ForeignKey('organization.Branch', null=True, blank=True, on_delete=models.SET_NULL)
    department = models.ForeignKey('organization.Department', null=True, blank=True, on_delete=models.SET_NULL)
    amount = models.DecimalField(max_digits=18, decimal_places=2, validators=[MinValueValidator(0)])
    expense_date = models.DateField(default=timezone.now)
    description = models.TextField(blank=True)
    receipt = models.FileField(upload_to='expense_receipts/', null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    approved_by = models.ForeignKey('accounts.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_expenses')
    approved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.number} — {self.title} (Rp {self.amount:,.0f})"

    def save(self, *args, **kwargs):
        if not self.number:
            y, m = timezone.now().year, timezone.now().month
            count = Expense.objects.filter(company=self.company, created_at__year=y, created_at__month=m).count() + 1
            self.number = f"EXP/{y}{m:02d}/{count:04d}"
        super().save(*args, **kwargs)
