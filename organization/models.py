"""
organization/models.py

Hierarki organisasi: Company → Branch → Department

Multi-company/multi-branch di-handle di sini.
Semua model operasional (Inventory, Purchasing, Finance) akan FK ke Company dan/atau Branch.
"""

from django.db import models
from django.utils.text import slugify
from core.models import NexusBaseModel


class Company(NexusBaseModel):
    """
    Top-level entity. Setiap data operasional terikat ke Company.

    Kenapa Company extends NexusBaseModel tapi created_by nullable?
    Karena Company pertama dibuat lewat management command saat setup awal,
    belum ada user yang login.
    """
    name = models.CharField(max_length=200)
    code = models.CharField(
        max_length=20, unique=True,
        help_text="Kode unik perusahaan, e.g. 'PT-ALPHA'. Auto-generate dari nama jika kosong."
    )
    legal_name = models.CharField(max_length=300, blank=True)
    tax_id = models.CharField(max_length=50, blank=True, help_text="NPWP")
    logo = models.ImageField(upload_to='company_logos/', null=True, blank=True)

    # Kontak
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)

    # Alamat
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    province = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=10, blank=True)
    country = models.CharField(max_length=100, default='Indonesia')

    # Keuangan
    currency = models.CharField(max_length=3, default='IDR', help_text="ISO 4217 currency code")
    fiscal_year_start = models.PositiveSmallIntegerField(
        default=1,
        help_text="Bulan awal tahun fiskal (1=Januari, 4=April, dst)."
    )

    class Meta:
        verbose_name_plural = 'Companies'
        ordering = ['name']

    def __str__(self):
        return f"{self.code} — {self.name}"

    def save(self, *args, **kwargs):
        if not self.code:
            base = slugify(self.name).upper().replace('-', '')[:10]
            self.code = base
        super().save(*args, **kwargs)

    @property
    def active_branches(self):
        return self.branches.filter(is_active=True)

    @property
    def active_departments(self):
        return self.departments.filter(is_active=True)


class Branch(NexusBaseModel):
    """
    Cabang/lokasi dari sebuah Company.
    Contoh: PT Alpha punya Cabang Jakarta, Cabang Surabaya, Cabang Bali.

    Inventory, Purchasing, dll bisa di-filter per branch.
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20)

    # Alamat cabang (bisa beda dengan company HQ)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    province = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=10, blank=True)

    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    is_headquarters = models.BooleanField(
        default=False,
        help_text="Tandai satu branch sebagai kantor pusat."
    )

    class Meta:
        unique_together = ['company', 'code']
        ordering = ['company', 'name']

    def __str__(self):
        return f"{self.company.code} / {self.code} — {self.name}"


class Department(NexusBaseModel):
    """
    Departemen dalam sebuah Company.
    Dipakai untuk: HR (siapa di departemen mana), Approval routing (finance dept approve invoice).

    Department bisa nested (parent-child) untuk struktur hierarki yang dalam.
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='departments')
    branch = models.ForeignKey(
        Branch, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='departments',
        help_text="Kosongkan jika departemen berlaku untuk semua cabang."
    )
    parent = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='sub_departments',
        help_text="Parent department untuk struktur hierarki."
    )

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20)
    description = models.TextField(blank=True)

    # Kepala departemen
    head = models.ForeignKey(
        'accounts.User', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='headed_departments',
    )

    class Meta:
        unique_together = ['company', 'code']
        ordering = ['company', 'name']

    def __str__(self):
        return f"{self.company.code} / {self.name}"

    def get_ancestors(self):
        """Return list department dari root ke parent terdekat."""
        ancestors = []
        current = self.parent
        while current:
            ancestors.insert(0, current)
            current = current.parent
        return ancestors

    def get_full_path(self):
        """Return 'Finance > Accounting > AP' style string."""
        ancestors = self.get_ancestors()
        parts = [d.name for d in ancestors] + [self.name]
        return ' > '.join(parts)
