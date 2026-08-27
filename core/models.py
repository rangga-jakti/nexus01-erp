"""
core/models.py — Abstract base models + cross-module engines
"""
import uuid
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone


class NexusBaseModel(models.Model):
    """Abstract base untuk semua model Nexus-01."""
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='%(app_label)s_%(class)s_created',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='%(app_label)s_%(class)s_updated',
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']

    def soft_delete(self, user=None):
        self.is_active = False
        self.updated_by = user
        self.save(update_fields=['is_active', 'updated_by', 'updated_at'])

    def restore(self, user=None):
        self.is_active = True
        self.updated_by = user
        self.save(update_fields=['is_active', 'updated_by', 'updated_at'])


class CompanyBoundModel(NexusBaseModel):
    """Extend NexusBaseModel untuk model yang terikat ke Company."""
    company = models.ForeignKey(
        'organization.Company',
        on_delete=models.CASCADE,
        related_name='%(app_label)s_%(class)s_set',
        db_index=True,
    )

    class Meta:
        abstract = True


class AuditLog(models.Model):
    """Immutable audit trail — tidak boleh diubah/dihapus setelah dibuat."""

    class Action(models.TextChoices):
        CREATE = 'CREATE', 'Create'
        UPDATE = 'UPDATE', 'Update'
        DELETE = 'DELETE', 'Delete'
        LOGIN = 'LOGIN', 'Login'
        LOGOUT = 'LOGOUT', 'Logout'
        APPROVE = 'APPROVE', 'Approve'
        REJECT = 'REJECT', 'Reject'
        EXPORT = 'EXPORT', 'Export'
        VIEW_SENSITIVE = 'VIEW_SENSITIVE', 'View Sensitive'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
        related_name='audit_logs', db_index=True,
    )
    company = models.ForeignKey(
        'organization.Company', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='audit_logs', db_index=True,
    )
    action = models.CharField(max_length=20, choices=Action.choices, db_index=True)

    content_type = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.SET_NULL)
    object_id = models.PositiveBigIntegerField(null=True, blank=True, db_index=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    object_repr = models.CharField(max_length=500, blank=True)

    changes = models.JSONField(default=dict, blank=True)
    message = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        default_permissions = ('view',)
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['company', 'timestamp']),
        ]

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.user} → {self.action} {self.object_repr}"

    @classmethod
    def log(cls, user, action, obj=None, company=None, changes=None,
            message='', ip_address=None, user_agent=''):
        entry = cls(
            user=user, company=company, action=action,
            message=message, changes=changes or {},
            ip_address=ip_address, user_agent=user_agent,
        )
        if obj is not None:
            entry.content_type = ContentType.objects.get_for_model(obj)
            entry.object_id = obj.pk
            entry.object_repr = str(obj)[:500]
        entry.save()
        return entry


class ApprovalRequest(models.Model):
    """Generic approval engine untuk semua modul."""

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        CANCELLED = 'CANCELLED', 'Cancelled'
        ESCALATED = 'ESCALATED', 'Escalated'

    class Priority(models.TextChoices):
        LOW = 'LOW', 'Low'
        NORMAL = 'NORMAL', 'Normal'
        HIGH = 'HIGH', 'High'
        URGENT = 'URGENT', 'Urgent'

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField(db_index=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    company = models.ForeignKey(
        'organization.Company', on_delete=models.CASCADE, related_name='approval_requests',
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='approval_requests_submitted',
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='approval_requests_to_review',
    )

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.NORMAL)
    level = models.PositiveSmallIntegerField(default=1)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)

    requested_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['status', 'company']),
            models.Index(fields=['approver', 'status']),
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return f"[{self.status}] {self.title}"

    def approve(self, approver, notes=''):
        self.status = self.Status.APPROVED
        self.approver = approver
        self.notes = notes
        self.reviewed_at = timezone.now()
        self.save()
        AuditLog.log(user=approver, action=AuditLog.Action.APPROVE, obj=self,
                     company=self.company, message=notes)

    def reject(self, approver, notes=''):
        self.status = self.Status.REJECTED
        self.approver = approver
        self.notes = notes
        self.reviewed_at = timezone.now()
        self.save()
        AuditLog.log(user=approver, action=AuditLog.Action.REJECT, obj=self,
                     company=self.company, message=notes)


class Notification(models.Model):
    class Type(models.TextChoices):
        APPROVAL = 'APPROVAL', 'Approval Request'
        STOCK_ALERT = 'STOCK_ALERT', 'Stock Alert'
        PAYMENT_DUE = 'PAYMENT_DUE', 'Payment Due'
        SYSTEM = 'SYSTEM', 'System'
        INFO = 'INFO', 'Info'

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications',
    )
    company = models.ForeignKey(
        'organization.Company', null=True, blank=True, on_delete=models.SET_NULL,
    )
    notification_type = models.CharField(max_length=20, choices=Type.choices, default=Type.INFO)
    title = models.CharField(max_length=200)
    message = models.TextField()
    url = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    approval_request = models.ForeignKey(
        ApprovalRequest, null=True, blank=True, on_delete=models.SET_NULL, related_name='notifications',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{'read' if self.is_read else 'unread'}] {self.recipient} — {self.title}"

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    @classmethod
    def send(cls, recipient, title, message, notification_type=Type.INFO,
             company=None, url='', approval_request=None):
        return cls.objects.create(
            recipient=recipient, title=title, message=message,
            notification_type=notification_type, company=company,
            url=url, approval_request=approval_request,
        )
