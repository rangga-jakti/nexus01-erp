from django.contrib import admin
from .models import Company, Branch, Department


class BranchInline(admin.TabularInline):
    model = Branch
    extra = 0
    fields = ['name', 'code', 'city', 'is_headquarters', 'is_active']


class DepartmentInline(admin.TabularInline):
    model = Department
    extra = 0
    fields = ['name', 'code', 'head', 'is_active']


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'city', 'currency', 'is_active', 'created_at']
    list_filter = ['is_active', 'country', 'currency']
    search_fields = ['name', 'code', 'legal_name']
    inlines = [BranchInline, DepartmentInline]
    readonly_fields = ['uid', 'created_at', 'updated_at']


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'company', 'city', 'is_headquarters', 'is_active']
    list_filter = ['company', 'is_headquarters', 'is_active']
    search_fields = ['name', 'code', 'company__name']


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'company', 'branch', 'head', 'is_active']
    list_filter = ['company', 'is_active']
    search_fields = ['name', 'code']
