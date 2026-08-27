"""
inventory/models.py

Modul inventory Nexus-01: Product → Warehouse → Stock → StockMovement

Relasi kunci:
- Setiap Stock = 1 Product di 1 Warehouse milik 1 Company
- Setiap mutasi stok (masuk/keluar) dicatat sebagai StockMovement
- StockMovement dibuat oleh sistem (via signal) ketika ada GoodsReceipt atau Delivery
- Tidak boleh ada yang mengubah Stock.quantity langsung — harus lewat StockMovement
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from core.models import CompanyBoundModel, NexusBaseModel


class ProductCategory(CompanyBoundModel):
    """Kategori produk — bisa nested (parent-child)."""
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20)
    parent = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='sub_categories',
    )
    description = models.TextField(blank=True)

    class Meta:
        unique_together = ['company', 'code']
        verbose_name_plural = 'Product Categories'

    def __str__(self):
        return f"{self.code} — {self.name}"


class UnitOfMeasure(CompanyBoundModel):
    """Satuan ukuran: pcs, kg, liter, box, carton, dll."""
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=10)
    symbol = models.CharField(max_length=10, blank=True)

    class Meta:
        unique_together = ['company', 'code']

    def __str__(self):
        return f"{self.code} ({self.name})"


class Product(CompanyBoundModel):
    """
    Master data produk.

    Setiap produk bisa berada di banyak Warehouse (via Stock).
    total_stock() menjumlahkan dari semua warehouse.
    """

    class ProductType(models.TextChoices):
        STORABLE = 'STORABLE', 'Storable Product'       # Punya stok fisik
        CONSUMABLE = 'CONSUMABLE', 'Consumable'          # Habis pakai, tidak di-track stok
        SERVICE = 'SERVICE', 'Service'                   # Jasa, tidak ada stok

    # Identifikasi
    sku = models.CharField(
        max_length=50,
        help_text="Stock Keeping Unit — kode unik internal"
    )
    barcode = models.CharField(max_length=100, blank=True)
    name = models.CharField(max_length=300)
    description = models.TextField(blank=True)

    product_type = models.CharField(
        max_length=20, choices=ProductType.choices, default=ProductType.STORABLE
    )
    category = models.ForeignKey(
        ProductCategory, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='products',
    )
    unit = models.ForeignKey(
        UnitOfMeasure, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='products',
    )

    # Harga
    purchase_price = models.DecimalField(
        max_digits=18, decimal_places=2, default=0,
        help_text="Harga beli default dari supplier"
    )
    selling_price = models.DecimalField(
        max_digits=18, decimal_places=2, default=0,
        help_text="Harga jual default"
    )

    # Stok control
    minimum_stock = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        validators=[MinValueValidator(0)],
        help_text="Batas stok minimum — trigger alert jika di bawah ini"
    )
    reorder_point = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Trigger automatic purchase request jika stok di bawah ini"
    )

    # Fisik
    weight = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['company', 'sku']
        ordering = ['name']

    def __str__(self):
        return f"[{self.sku}] {self.name}"

    @property
    def total_stock(self):
        """Total stok di semua warehouse."""
        result = self.stocks.filter(is_active=True).aggregate(
            total=models.Sum('quantity')
        )
        return result['total'] or 0

    @property
    def is_low_stock(self):
        return self.product_type == self.ProductType.STORABLE and \
               self.total_stock <= self.minimum_stock

    @property
    def needs_reorder(self):
        return self.product_type == self.ProductType.STORABLE and \
               self.reorder_point > 0 and self.total_stock <= self.reorder_point


class Warehouse(CompanyBoundModel):
    """
    Gudang/lokasi penyimpanan.
    Bisa di-assign ke Branch tertentu atau berlaku global untuk company.
    """
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20)
    branch = models.ForeignKey(
        'organization.Branch', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='warehouses',
    )
    address = models.TextField(blank=True)
    is_default = models.BooleanField(
        default=False,
        help_text="Gudang default yang dipilih otomatis saat transaksi"
    )
    capacity = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Kapasitas gudang dalam satuan volume/berat (opsional)"
    )
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['company', 'code']
        ordering = ['name']

    def __str__(self):
        return f"{self.code} — {self.name}"

    def save(self, *args, **kwargs):
        if self.is_default:
            Warehouse.objects.filter(
                company=self.company, is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class Stock(CompanyBoundModel):
    """
    Posisi stok: berapa banyak Product X ada di Warehouse Y.

    ATURAN KERAS:
    - Jangan pernah update Stock.quantity langsung dari view/form.
    - Selalu buat StockMovement, lalu signal yang update Stock.
    - Ini memastikan setiap perubahan stok terekam dan bisa di-audit.
    """
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='stocks'
    )
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.CASCADE, related_name='stocks'
    )
    quantity = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        validators=[MinValueValidator(0)],
    )
    reserved_quantity = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        validators=[MinValueValidator(0)],
        help_text="Stok yang sudah di-reserve untuk SO yang belum dikirim"
    )
    last_movement_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['product', 'warehouse']
        ordering = ['product__name', 'warehouse__name']

    def __str__(self):
        return f"{self.product.sku} @ {self.warehouse.code}: {self.available_quantity}"

    @property
    def available_quantity(self):
        """Stok yang benar-benar tersedia (total - reserved)."""
        return max(0, self.quantity - self.reserved_quantity)

    def add_stock(self, qty, movement_type, reference=None, notes='', user=None):
        """
        Tambah stok via StockMovement. Ini cara SATU-SATUNYA untuk menambah stok.
        """
        if qty <= 0:
            raise ValueError("Quantity harus > 0")
        movement = StockMovement.objects.create(
            company=self.company,
            stock=self,
            product=self.product,
            warehouse=self.warehouse,
            movement_type=movement_type,
            quantity=qty,
            quantity_before=self.quantity,
            quantity_after=self.quantity + qty,
            reference=reference or '',
            notes=notes,
            created_by=user,
        )
        # Update stock quantity
        self.quantity = models.F('quantity') + qty
        self.last_movement_at = timezone.now()
        self.save(update_fields=['quantity', 'last_movement_at'])
        self.refresh_from_db()
        return movement

    def reduce_stock(self, qty, movement_type, reference=None, notes='', user=None):
        """Kurangi stok. Raise ValueError jika stok tidak cukup."""
        if qty <= 0:
            raise ValueError("Quantity harus > 0")
        if self.available_quantity < qty:
            raise ValueError(
                f"Stok tidak cukup. Tersedia: {self.available_quantity}, diminta: {qty}"
            )
        movement = StockMovement.objects.create(
            company=self.company,
            stock=self,
            product=self.product,
            warehouse=self.warehouse,
            movement_type=movement_type,
            quantity=-qty,
            quantity_before=self.quantity,
            quantity_after=self.quantity - qty,
            reference=reference or '',
            notes=notes,
            created_by=user,
        )
        self.quantity = models.F('quantity') - qty
        self.last_movement_at = timezone.now()
        self.save(update_fields=['quantity', 'last_movement_at'])
        self.refresh_from_db()
        return movement


class StockMovement(models.Model):
    """
    Immutable log setiap perubahan stok.
    Ini adalah "source of truth" — dari sinilah bisa rekonstruksi posisi stok
    di titik waktu manapun.

    Jangan hapus record ini. Kalau ada kesalahan, buat reversal movement.
    """

    class MovementType(models.TextChoices):
        # Masuk
        PURCHASE_RECEIPT = 'PURCHASE_RECEIPT', 'Goods Receipt (Purchase)'
        SALES_RETURN = 'SALES_RETURN', 'Sales Return'
        ADJUSTMENT_IN = 'ADJUSTMENT_IN', 'Stock Adjustment (+)'
        TRANSFER_IN = 'TRANSFER_IN', 'Transfer Masuk'
        OPENING_STOCK = 'OPENING_STOCK', 'Opening Stock'
        # Keluar
        SALES_DELIVERY = 'SALES_DELIVERY', 'Sales Delivery'
        PURCHASE_RETURN = 'PURCHASE_RETURN', 'Purchase Return'
        ADJUSTMENT_OUT = 'ADJUSTMENT_OUT', 'Stock Adjustment (-)'
        TRANSFER_OUT = 'TRANSFER_OUT', 'Transfer Keluar'
        DAMAGED = 'DAMAGED', 'Barang Rusak/Hilang'

    company = models.ForeignKey(
        'organization.Company', on_delete=models.CASCADE, related_name='stock_movements'
    )
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='movements')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='movements')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='movements')

    movement_type = models.CharField(max_length=30, choices=MovementType.choices, db_index=True)

    # quantity bisa negatif untuk mutasi keluar
    quantity = models.DecimalField(max_digits=14, decimal_places=2)
    quantity_before = models.DecimalField(max_digits=14, decimal_places=2)
    quantity_after = models.DecimalField(max_digits=14, decimal_places=2)

    # Referensi ke dokumen sumber
    reference = models.CharField(
        max_length=100, blank=True, db_index=True,
        help_text="Nomor PO, SO, GR, dll yang memicu movement ini"
    )
    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        'accounts.User', null=True, on_delete=models.SET_NULL, related_name='stock_movements'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', 'created_at']),
            models.Index(fields=['warehouse', 'created_at']),
            models.Index(fields=['movement_type', 'created_at']),
        ]
        # Immutable — tidak boleh diubah
        default_permissions = ('view', 'add')

    def __str__(self):
        sign = '+' if self.quantity > 0 else ''
        return f"[{self.movement_type}] {self.product.sku}: {sign}{self.quantity} @ {self.warehouse.code}"
