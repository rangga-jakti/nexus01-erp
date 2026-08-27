from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User, Role, Permission, RolePermission, UserCompany


class UserCompanyInline(admin.TabularInline):
    model = UserCompany
    fk_name = 'user'
    extra = 0
    fields = ['company', 'role', 'is_default', 'is_active']


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    inlines = [UserCompanyInline]
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_active', 'is_verified', 'created_at']
    list_filter = ['is_active', 'is_verified', 'is_staff', 'is_superuser']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    fieldsets = DjangoUserAdmin.fieldsets + (
        ('Nexus-01', {'fields': ('phone', 'avatar', 'bio', 'is_verified')}),
    )


class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 0
    fields = ['permission', 'granted_by', 'granted_at']
    readonly_fields = ['granted_at']


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_system', 'permission_count']
    list_filter = ['is_system']
    search_fields = ['name', 'code']
    inlines = [RolePermissionInline]

    def permission_count(self, obj):
        return obj.permissions.count()
    permission_count.short_description = '# Permissions'


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'module']
    list_filter = ['module']
    search_fields = ['code', 'name']


@admin.register(UserCompany)
class UserCompanyAdmin(admin.ModelAdmin):
    list_display = ['user', 'company', 'role', 'is_default', 'is_active', 'joined_at']
    list_filter = ['is_active', 'is_default', 'company']
    search_fields = ['user__username', 'company__name']
