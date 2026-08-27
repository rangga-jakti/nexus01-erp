"""
accounts/models.py

Custom User model + RBAC (Role-Based Access Control).

Struktur:
  User (custom AbstractUser)
    └── UserCompany (junction table)
          ├── Company
          └── Role
                └── RolePermission
                      └── Permission
"""

import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError


# ---------------------------------------------------------------------------
# Permission & Role
# ---------------------------------------------------------------------------

class Permission(models.Model):
    """
    Atomic permission unit. Format: 'module.action'
    Contoh: 'purchasing.create_po', 'inventory.view_stock', 'finance.approve_payment'

    Kenapa tidak pakai Django built-in permissions?
    Built-in Django permissions bekerja di level model, bukan business action.
    Kita butuh permission yang lebih granular dan bermakna bisnis,
    seperti 'purchasing.approve_po_above_10m' yang tidak bisa direpresentasikan
    oleh 'purchasing | purchase order | Can change purchase order'.
    """
    code = models.CharField(
        max_length=100, unique=True,
        help_text="Format: 'modul.aksi' — e.g. 'purchasing.approve_po'"
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    module = models.CharField(max_length=50, db_index=True)

    class Meta:
        ordering = ['module', 'code']

    def __str__(self):
        return f"{self.code} ({self.name})"


class Role(models.Model):
    """
    Role adalah kumpulan Permission. User diberi Role, bukan Permission langsung.

    Contoh role:
    - Super Admin: semua permission
    - Finance Manager: semua finance.*, bisa view inventory.*
    - Warehouse Staff: inventory.*, tidak bisa lihat finance
    - Viewer: semua *.view_* saja
    """
    name = models.CharField(max_length=100)
    code = models.CharField(
        max_length=50, unique=True,
        help_text="Slug unik, e.g. 'finance_manager'"
    )
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(
        Permission,
        through='RolePermission',
        related_name='roles',
        blank=True,
    )
    is_system = models.BooleanField(
        default=False,
        help_text="True = role bawaan sistem, tidak bisa dihapus user."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_permission_codes(self):
        """Return set of permission codes untuk quick lookup."""
        return set(self.permissions.values_list('code', flat=True))


class RolePermission(models.Model):
    """Through model untuk Role ↔ Permission."""
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_permissions')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    granted_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.ForeignKey(
        'accounts.User', null=True, on_delete=models.SET_NULL,
        related_name='granted_permissions',
    )

    class Meta:
        unique_together = ['role', 'permission']

    def __str__(self):
        return f"{self.role} → {self.permission.code}"


# ---------------------------------------------------------------------------
# Custom User Model
# ---------------------------------------------------------------------------

class User(AbstractUser):
    """
    Custom User model Nexus-01.

    Mengextend AbstractUser (bukan AbstractBaseUser) supaya kita tetap dapat
    semua fitur bawaan Django (admin, auth, session) tapi bisa tambah field sendiri.

    PENTING: Model ini harus didefinisikan sebelum `python manage.py migrate` pertama.
    Kalau sudah terlanjur migrate dengan default User, migrasi akan sangat painful.
    Itulah kenapa ini Phase 1 dan harus dikerjakan paling pertama.
    """
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    # Override email — jadikan unik dan required
    email = models.EmailField(unique=True)

    # Profil
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(blank=True)

    # Status
    is_verified = models.BooleanField(
        default=False,
        help_text="True jika email sudah diverifikasi."
    )

    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity = models.DateTimeField(null=True, blank=True)

    # Companies yang bisa diakses user ini (via UserCompany junction)
    companies = models.ManyToManyField(
        'organization.Company',
        through='UserCompany',
        through_fields=('user', 'company'),
        related_name='users',
        blank=True,
    )

    class Meta:
        swappable = 'AUTH_USER_MODEL'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['uid']),
        ]

    def __str__(self):
        return f"{self.get_full_name() or self.username} <{self.email}>"

    def get_companies(self):
        """Semua company yang bisa diakses user ini."""
        return self.companies.filter(is_active=True, usercompany__is_active=True)

    def get_role_in_company(self, company):
        """Role user di company tertentu."""
        try:
            uc = self.usercompany_set.get(company=company, is_active=True)
            return uc.role
        except UserCompany.DoesNotExist:
            return None

    def has_nexus_perm(self, perm_code, company=None):
        """
        Check apakah user punya permission tertentu di company tertentu.

        Contoh: user.has_nexus_perm('purchasing.create_po', company=pt_alpha)

        Superuser selalu True. Sisanya cek via role di company tersebut.
        """
        if self.is_superuser:
            return True
        if company is None:
            return False

        role = self.get_role_in_company(company)
        if role is None:
            return False

        return role.permissions.filter(code=perm_code).exists()

    def get_all_permissions_in_company(self, company):
        """Return set semua permission codes user di company tertentu."""
        if self.is_superuser:
            return {'*'}  # Superuser punya semua
        role = self.get_role_in_company(company)
        if role is None:
            return set()
        return role.get_permission_codes()


# ---------------------------------------------------------------------------
# UserCompany — junction table User ↔ Company dengan Role
# ---------------------------------------------------------------------------

class UserCompany(models.Model):
    """
    Relasi User ke Company dengan Role spesifik per company.

    Satu user bisa punya role berbeda di company berbeda:
      Andi → PT Alpha (Finance Manager)
      Andi → PT Beta  (Viewer)
      Andi → PT Gamma (Super Admin)

    is_default: company yang langsung terbuka saat user login pertama kali.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    company = models.ForeignKey('organization.Company', on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.PROTECT)

    is_default = models.BooleanField(
        default=False,
        help_text="Company default yang aktif saat user login."
    )
    is_active = models.BooleanField(default=True, db_index=True)

    joined_at = models.DateTimeField(auto_now_add=True)
    invited_by = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='user_invitations',
    )

    class Meta:
        unique_together = ['user', 'company']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['company', 'is_active']),
        ]

    def __str__(self):
        return f"{self.user} @ {self.company} [{self.role}]"

    def save(self, *args, **kwargs):
        """
        Pastikan hanya satu company yang jadi default per user.
        Kalau is_default=True, set semua UserCompany lain milik user ini ke False dulu.
        """
        if self.is_default:
            UserCompany.objects.filter(
                user=self.user, is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_default_company(cls, user):
        """Return company default user. Kalau belum ada, ambil yang pertama."""
        uc = cls.objects.filter(user=user, is_active=True).select_related('company')
        default = uc.filter(is_default=True).first()
        if default:
            return default.company
        first = uc.first()
        return first.company if first else None
