"""
core/templatetags/nexus_tags.py
Custom template tags & filters untuk Nexus-01.
"""
from django import template
from django.utils.numberformat import format as number_format

register = template.Library()

@register.filter
def idr(value):
    """Format angka ke Rupiah: 1500000 → Rp 1.500.000"""
    try:
        value = float(value or 0)
        if value >= 1_000_000_000:
            return f"Rp {value/1_000_000_000:.1f}M"
        if value >= 1_000_000:
            return f"Rp {value/1_000_000:.1f}jt"
        return f"Rp {value:,.0f}".replace(',', '.')
    except (TypeError, ValueError):
        return "Rp 0"

@register.filter
def stock_color(value, minimum=0):
    """Return Tailwind color class berdasarkan level stok."""
    try:
        v, m = float(value or 0), float(minimum or 0)
        if v == 0:
            return "text-red-600"
        if m > 0 and v <= m:
            return "text-amber-600"
        return "text-green-600"
    except (TypeError, ValueError):
        return "text-gray-400"

@register.filter
def stock_bg(value, minimum=0):
    try:
        v, m = float(value or 0), float(minimum or 0)
        if v == 0:
            return "bg-red-50 text-red-700 border-red-200"
        if m > 0 and v <= m:
            return "bg-amber-50 text-amber-700 border-amber-200"
        return "bg-green-50 text-green-700 border-green-200"
    except (TypeError, ValueError):
        return "bg-gray-50 text-gray-500 border-gray-200"

@register.filter
def movement_color(value):
    """Warna untuk qty movement — hijau jika positif, merah jika negatif."""
    try:
        return "text-green-600" if float(value) > 0 else "text-red-600"
    except (TypeError, ValueError):
        return "text-gray-500"

@register.filter
def movement_sign(value):
    try:
        f = float(value)
        return f"+{f:,.2f}" if f > 0 else f"{f:,.2f}"
    except (TypeError, ValueError):
        return str(value)

@register.inclusion_tag('core/partials/breadcrumb.html')
def breadcrumb(*items):
    """{% breadcrumb 'Inventory' 'Products' %}"""
    return {'items': items}

@register.filter
def perm(user_perms, perm_code):
    """{{ active_permissions|perm:'inventory.create_product' }}"""
    return perm_code in user_perms

@register.filter
def get_item(dictionary, key):
    """{{ my_dict|get_item:key }} — dict lookup di template."""
    if isinstance(dictionary, dict):
        return dictionary.get(key, 0)
    return 0
