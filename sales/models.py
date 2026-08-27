"""sales/models.py — Customer, Quotation, SalesOrder, Delivery"""
from django.db import models
from django.core.validators import MinValueValidator
from core.models import CompanyBoundModel


class Customer(CompanyBoundModel):
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=300)
    contact_person = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    payment_terms_days = models.PositiveIntegerField(default=30)
    credit_limit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['company', 'code']
        ordering = ['name']

    def __str__(self):
        return f"[{self.code}] {self.name}"


class Quotation(CompanyBoundModel):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SENT = 'SENT', 'Terkirim'
        ACCEPTED = 'ACCEPTED', 'Diterima'
        REJECTED = 'REJECTED', 'Ditolak'
        EXPIRED = 'EXPIRED', 'Kadaluarsa'
        CANCELLED = 'CANCELLED', 'Dibatalkan'

    number = models.CharField(max_length=30, unique=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='quotations')
    branch = models.ForeignKey('organization.Branch', null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    quotation_date = models.DateField(auto_now_add=True)
    valid_until = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    terms_conditions = models.TextField(blank=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=11)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.number} — {self.customer.name}"

    def save(self, *args, **kwargs):
        if not self.number:
            from django.utils import timezone
            y, m = timezone.now().year, timezone.now().month
            count = Quotation.objects.filter(company=self.company, created_at__year=y, created_at__month=m).count() + 1
            self.number = f"QT/{y}{m:02d}/{count:04d}"
        super().save(*args, **kwargs)

    @property
    def subtotal(self):
        return sum(i.subtotal for i in self.items.all())

    @property
    def total_amount(self):
        return self.subtotal + (self.subtotal * self.tax_rate / 100) - self.discount_amount


class QuotationItem(models.Model):
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('inventory.Product', on_delete=models.PROTECT)
    description = models.CharField(max_length=300, blank=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    unit = models.ForeignKey('inventory.UnitOfMeasure', null=True, blank=True, on_delete=models.SET_NULL)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    @property
    def subtotal(self):
        return self.quantity * self.unit_price * (1 - self.discount_percent / 100)


class SalesOrder(CompanyBoundModel):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PENDING = 'PENDING', 'Menunggu Approval'
        CONFIRMED = 'CONFIRMED', 'Dikonfirmasi'
        PARTIAL = 'PARTIAL', 'Sebagian Dikirim'
        COMPLETED = 'COMPLETED', 'Selesai'
        CANCELLED = 'CANCELLED', 'Dibatalkan'

    number = models.CharField(max_length=30, unique=True, blank=True)
    quotation = models.OneToOneField(Quotation, null=True, blank=True, on_delete=models.SET_NULL, related_name='sales_order')
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='sales_orders')
    branch = models.ForeignKey('organization.Branch', null=True, blank=True, on_delete=models.SET_NULL)
    warehouse = models.ForeignKey('inventory.Warehouse', null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    order_date = models.DateField(auto_now_add=True)
    expected_delivery_date = models.DateField(null=True, blank=True)
    shipping_address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=11)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.number} — {self.customer.name}"

    def save(self, *args, **kwargs):
        if not self.number:
            from django.utils import timezone
            y, m = timezone.now().year, timezone.now().month
            count = SalesOrder.objects.filter(company=self.company, created_at__year=y, created_at__month=m).count() + 1
            self.number = f"SO/{y}{m:02d}/{count:04d}"
        super().save(*args, **kwargs)

    @property
    def subtotal(self):
        return sum(i.subtotal for i in self.items.all())

    @property
    def total_amount(self):
        return self.subtotal + (self.subtotal * self.tax_rate / 100) - self.discount_amount


class SalesOrderItem(models.Model):
    so = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('inventory.Product', on_delete=models.PROTECT)
    description = models.CharField(max_length=300, blank=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    unit = models.ForeignKey('inventory.UnitOfMeasure', null=True, blank=True, on_delete=models.SET_NULL)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    quantity_delivered = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    @property
    def subtotal(self):
        return self.quantity * self.unit_price

    @property
    def quantity_pending(self):
        return max(0, self.quantity - self.quantity_delivered)


class Delivery(CompanyBoundModel):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PACKED = 'PACKED', 'Dikemas'
        SHIPPED = 'SHIPPED', 'Dikirim'
        DELIVERED = 'DELIVERED', 'Terkirim'
        CANCELLED = 'CANCELLED', 'Dibatalkan'

    number = models.CharField(max_length=30, unique=True, blank=True)
    so = models.ForeignKey(SalesOrder, on_delete=models.PROTECT, related_name='deliveries')
    warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    delivery_date = models.DateField(null=True, blank=True)
    shipping_method = models.CharField(max_length=100, blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.number} — {self.so.number}"

    def save(self, *args, **kwargs):
        if not self.number:
            from django.utils import timezone
            y, m = timezone.now().year, timezone.now().month
            count = Delivery.objects.filter(company=self.company, created_at__year=y, created_at__month=m).count() + 1
            self.number = f"DO/{y}{m:02d}/{count:04d}"
        super().save(*args, **kwargs)

    def confirm_delivery(self, user):
        """Konfirmasi delivery → kurangi stok."""
        from django.utils import timezone as tz
        from inventory.models import Stock

        if self.status not in [self.Status.DRAFT, self.Status.PACKED, self.Status.SHIPPED]:
            raise ValueError("Status tidak valid untuk konfirmasi delivery.")

        for item in self.items.select_related('so_item__product'):
            product = item.so_item.product
            stock = Stock.objects.get(company=self.company, product=product, warehouse=self.warehouse)
            stock.reduce_stock(
                qty=item.quantity,
                movement_type='SALES_DELIVERY',
                reference=self.number,
                notes=f"Delivery {self.number} untuk SO {self.so.number}",
                user=user,
            )
            item.so_item.quantity_delivered += item.quantity
            item.so_item.save(update_fields=['quantity_delivered'])

        self.status = self.Status.DELIVERED
        self.delivered_at = tz.now()
        self.save()


class DeliveryItem(models.Model):
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE, related_name='items')
    so_item = models.ForeignKey(SalesOrderItem, on_delete=models.PROTECT, related_name='delivery_items')
    quantity = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    notes = models.TextField(blank=True)
