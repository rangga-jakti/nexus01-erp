from django.contrib import admin
from .models import AuditLog, ApprovalRequest, Notification

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'action', 'object_repr', 'company', 'ip_address']
    list_filter = ['action', 'company']
    search_fields = ['user__username', 'object_repr', 'message']
    readonly_fields = ['user', 'company', 'action', 'content_type', 'object_id',
                       'object_repr', 'changes', 'message', 'ip_address', 'user_agent', 'timestamp']
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'priority', 'requested_by', 'approver', 'company', 'requested_at']
    list_filter = ['status', 'priority', 'company']
    search_fields = ['title', 'requested_by__username']
    readonly_fields = ['requested_at', 'reviewed_at']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'recipient', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read']
    search_fields = ['title', 'recipient__username']
