"""
purchasing/models.py

Alur: PurchaseRequest → (Approval) → PurchaseOrder → GoodsReceipt → (Stock++)

State machine:
  PR:   DRAFT → PENDING → APPROVED/REJECTED → CANCELLED
  PO:   DRAFT → SENT → CONFIRMED → PARTIAL → COMPLETED → CANCELLED
  GR:   DRAFT → CONFIRMED
"""

from django.db import models
from django.core.validators import MinValueValidator
from core.models import CompanyBoundModel


def generate_pr_number(company):
    from django.utils import timezone
    year = timezone.now().year
    month = timezone.now().month
    count = PurchaseRequest.objects.filter(
        company=company,
        created_at__year=year,
        created_at__month=month,
    ).count() + 1
    return f"PR/{year}{month:02d}/{count:04d}"


def generate_po_number(company):
    from django.utils import timezone
    year = timezone.now().year
    month = timezone.now().month
    count = PurchaseOrder.objects.filter(
        company=company,
        created_at__year=year,
        created_at__month=month,
    ).count() + 1
    return f"PO/{year}{month:02d}/{count:04d}"


def generate_gr_number(company):
    from django.utils import timezone
    year = timezone.now().year
    month = timezone.now().month
    count = GoodsReceipt.objects.filter(
        company=company,
        created_at__year=year,
        created_at__month=month,
    ).count() + 1
    return f"GR/{year}{month:02d}/{count:04d}"


class Supplier(CompanyBoundModel):
    """Master data supplier."""
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=300)
    legal_name = models.CharField(max_length=300, blank=True)
    tax_id = models.CharField(max_length=50, blank=True, help_text="NPWP Supplier")

    contact_person = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)

    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    payment_terms_days = models.PositiveIntegerField(
        default=30,
        help_text="Jangka waktu pembayaran dalam hari (NET 30, dll)"
    )
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['company', 'code']
        ordering = ['name']

    def __str__(self):
        return f"[{self.code}] {self.name}"


class PurchaseRequest(CompanyBoundModel):
    """
    Purchase Request — permintaan pembelian dari internal.

    Dibuat oleh siapapun yang butuh barang/jasa.
    Harus di-approve oleh Manager sebelum jadi PO.
    """

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PENDING = 'PENDING', 'Menunggu Approval'
        APPROVED = 'APPROVED', 'Disetujui'
        REJECTED = 'REJECTED', 'Ditolak'
        CANCELLED = 'CANCELLED', 'Dibatalkan'
        PO_CREATED = 'PO_CREATED', 'PO Sudah Dibuat'

    number = models.CharField(max_length=30, unique=True, blank=True)
    title = models.CharField(max_length=300)
    branch = models.ForeignKey(
        'organization.Branch', null=True, blank=True, on_delete=models.SET_NULL
    )
    department = models.ForeignKey(
        'organization.Department', null=True, blank=True, on_delete=models.SET_NULL
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)

    # Supplier yang disarankan (opsional, approver bisa ganti)
    suggested_supplier = models.ForeignKey(
        Supplier, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='purchase_requests',
    )
    required_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)

    # Timestamps workflow
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        'accounts.User', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='approved_prs',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.number} — {self.title}"

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = generate_pr_number(self.company)
        super().save(*args, **kwargs)

    @property
    def total_amount(self):
        return sum(item.subtotal for item in self.items.all())

    def submit_for_approval(self, user):
        """Ubah status ke PENDING dan buat ApprovalRequest."""
        from django.utils import timezone
        from core.models import ApprovalRequest, Notification

        self.status = self.Status.PENDING
        self.submitted_at = timezone.now()
        self.save()

        # Tentukan approver (kepala departemen atau manager)
        approver = None
        if self.department and self.department.head:
            approver = self.department.head

        # Buat ApprovalRequest
        approval = ApprovalRequest.objects.create(
            content_type_id=self._meta.app_label,
            company=self.company,
            requested_by=user,
            approver=approver,
            title=f"Purchase Request: {self.number}",
            description=self.title,
            amount=self.total_amount,
        )

        # Set content type properly
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(self)
        approval.content_type = ct
        approval.object_id = self.pk
        approval.save()

        # Kirim notifikasi ke approver
        if approver:
            Notification.send(
                recipient=approver,
                title=f"Purchase Request Baru: {self.number}",
                message=f"{user.get_full_name()} meminta approval untuk {self.title}",
                notification_type=Notification.Type.APPROVAL,
                company=self.company,
                approval_request=approval,
            )

        return approval


class PurchaseRequestItem(models.Model):
    """Line item dari Purchase Request."""
    pr = models.ForeignKey(PurchaseRequest, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(
        'inventory.Product', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='pr_items',
    )
    # Kalau produk belum ada di master, bisa tulis deskripsi manual
    description = models.CharField(max_length=300, blank=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    unit = models.ForeignKey(
        'inventory.UnitOfMeasure', null=True, blank=True, on_delete=models.SET_NULL
    )
    estimated_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    def __str__(self):
        name = self.product.name if self.product else self.description
        return f"{name} × {self.quantity}"

    @property
    def subtotal(self):
        return self.quantity * self.estimated_price


class PurchaseOrder(CompanyBoundModel):
    """
    Purchase Order — dokumen resmi pemesanan ke supplier.
    Dibuat setelah PR di-approve.
    """

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SENT = 'SENT', 'Terkirim ke Supplier'
        CONFIRMED = 'CONFIRMED', 'Dikonfirmasi Supplier'
        PARTIAL = 'PARTIAL', 'Sebagian Diterima'
        COMPLETED = 'COMPLETED', 'Selesai'
        CANCELLED = 'CANCELLED', 'Dibatalkan'

    number = models.CharField(max_length=30, unique=True, blank=True)
    pr = models.ForeignKey(
        PurchaseRequest, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='purchase_orders',
        help_text="PR yang menghasilkan PO ini (opsional jika PO direct)"
    )
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='purchase_orders')
    branch = models.ForeignKey('organization.Branch', null=True, blank=True, on_delete=models.SET_NULL)
    warehouse = models.ForeignKey('inventory.Warehouse', null=True, blank=True, on_delete=models.SET_NULL)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)

    order_date = models.DateField(auto_now_add=True)
    expected_date = models.DateField(null=True, blank=True)

    # Terms
    payment_terms = models.CharField(max_length=100, blank=True, help_text="e.g. NET 30, COD")
    shipping_address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    supplier_reference = models.CharField(max_length=100, blank=True, help_text="Nomor PO dari sisi supplier")

    # Tax
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=11)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    sent_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.number} — {self.supplier.name}"

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = generate_po_number(self.company)
        super().save(*args, **kwargs)

    @property
    def subtotal(self):
        return sum(item.subtotal for item in self.items.all())

    @property
    def tax_amount(self):
        return self.subtotal * (self.tax_rate / 100)

    @property
    def total_amount(self):
        return self.subtotal + self.tax_amount - self.discount_amount


class PurchaseOrderItem(models.Model):
    """Line item Purchase Order."""
    po = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    pr_item = models.ForeignKey(
        PurchaseRequestItem, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='po_items',
    )
    product = models.ForeignKey('inventory.Product', on_delete=models.PROTECT, related_name='po_items')
    description = models.CharField(max_length=300, blank=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    unit = models.ForeignKey('inventory.UnitOfMeasure', null=True, blank=True, on_delete=models.SET_NULL)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    quantity_received = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    @property
    def subtotal(self):
        return self.quantity * self.unit_price

    @property
    def quantity_pending(self):
        return max(0, self.quantity - self.quantity_received)

    def __str__(self):
        return f"{self.product.name} × {self.quantity}"


class GoodsReceipt(CompanyBoundModel):
    """
    Goods Receipt — pencatatan barang yang datang dari supplier.
    Ini yang trigger penambahan stok di Inventory.

    Ketika GR di-confirm:
    → Signal dikirim ke inventory
    → Stock.add_stock() dipanggil untuk setiap item
    → StockMovement dibuat dengan type PURCHASE_RECEIPT
    → PO status di-update (PARTIAL atau COMPLETED)
    """

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        CONFIRMED = 'CONFIRMED', 'Dikonfirmasi'
        CANCELLED = 'CANCELLED', 'Dibatalkan'

    number = models.CharField(max_length=30, unique=True, blank=True)
    po = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name='goods_receipts')
    warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.PROTECT, related_name='goods_receipts')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    receipt_date = models.DateField(auto_now_add=True)
    delivery_note = models.CharField(max_length=100, blank=True, help_text="Nomor surat jalan dari supplier")
    notes = models.TextField(blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.number} — {self.po.number}"

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = generate_gr_number(self.company)
        super().save(*args, **kwargs)

    def confirm(self, user):
        """
        Konfirmasi GR: proses semua item → update stok → update PO status.
        Ini business logic utama yang menghubungkan Purchasing dengan Inventory.
        """
        from django.utils import timezone
        from inventory.models import Stock

        if self.status != self.Status.DRAFT:
            raise ValueError("Hanya GR berstatus Draft yang bisa dikonfirmasi.")

        for item in self.items.select_related('po_item__product'):
            product = item.po_item.product
            warehouse = self.warehouse

            # Get or create Stock record untuk product ini di warehouse ini
            stock, created = Stock.objects.get_or_create(
                company=self.company,
                product=product,
                warehouse=warehouse,
                defaults={'quantity': 0}
            )

            # Tambah stok — ini yang create StockMovement
            stock.add_stock(
                qty=item.quantity_received,
                movement_type='PURCHASE_RECEIPT',
                reference=self.number,
                notes=f"Goods Receipt {self.number} dari PO {self.po.number}",
                user=user,
            )

            # Update quantity received di PO item
            item.po_item.quantity_received += item.quantity_received
            item.po_item.save(update_fields=['quantity_received'])

        # Update status GR
        self.status = self.Status.CONFIRMED
        self.confirmed_at = timezone.now()
        self.updated_by = user
        self.save()

        # Update status PO
        po_items = self.po.items.all()
        all_received = all(item.quantity_pending == 0 for item in po_items)
        self.po.status = PurchaseOrder.Status.COMPLETED if all_received else PurchaseOrder.Status.PARTIAL
        self.po.save(update_fields=['status'])

        from core.models import AuditLog
        AuditLog.log(
            user=user, action=AuditLog.Action.APPROVE, obj=self,
            company=self.company,
            message=f"GR {self.number} dikonfirmasi — stok diupdate",
        )


class GoodsReceiptItem(models.Model):
    """Line item Goods Receipt."""
    gr = models.ForeignKey(GoodsReceipt, on_delete=models.CASCADE, related_name='items')
    po_item = models.ForeignKey(PurchaseOrderItem, on_delete=models.PROTECT, related_name='gr_items')
    quantity_received = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Quantity yang benar-benar diterima (bisa berbeda dengan PO jika ada kekurangan)"
    )
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.po_item.product.name} × {self.quantity_received}"
