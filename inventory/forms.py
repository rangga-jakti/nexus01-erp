"""
inventory/forms.py
"""
from django import forms
from .models import Product, ProductCategory, UnitOfMeasure, Warehouse, StockMovement


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'sku', 'name', 'barcode', 'product_type', 'category', 'unit',
            'purchase_price', 'selling_price', 'minimum_stock', 'reorder_point',
            'weight', 'image', 'description', 'notes',
        ]
        widgets = {
            'sku': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. PRD-001'}),
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Nama produk'}),
            'barcode': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Barcode (opsional)'}),
            'product_type': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'unit': forms.Select(attrs={'class': 'form-select'}),
            'purchase_price': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0'}),
            'minimum_stock': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0'}),
            'reorder_point': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0'}),
            'weight': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.001', 'min': '0'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            self.fields['category'].queryset = ProductCategory.objects.filter(
                company=company, is_active=True
            )
            self.fields['unit'].queryset = UnitOfMeasure.objects.filter(
                company=company, is_active=True
            )
        self.fields['category'].empty_label = '— Pilih Kategori —'
        self.fields['unit'].empty_label = '— Pilih Satuan —'
        self.fields['category'].required = False
        self.fields['unit'].required = False
        self.fields['barcode'].required = False
        self.fields['weight'].required = False
        self.fields['image'].required = False
        self.fields['description'].required = False
        self.fields['notes'].required = False


class ProductCategoryForm(forms.ModelForm):
    class Meta:
        model = ProductCategory
        fields = ['code', 'name', 'parent', 'description']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-input'}),
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'parent': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            self.fields['parent'].queryset = ProductCategory.objects.filter(
                company=company, is_active=True
            )
        self.fields['parent'].required = False
        self.fields['description'].required = False


class UOMForm(forms.ModelForm):
    class Meta:
        model = UnitOfMeasure
        fields = ['code', 'name', 'symbol']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. PCS'}),
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Pieces'}),
            'symbol': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. pcs'}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)


class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ['code', 'name', 'branch', 'address', 'is_default', 'capacity', 'notes']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. WH-JKT'}),
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Nama gudang'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'address': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            from organization.models import Branch
            self.fields['branch'].queryset = Branch.objects.filter(
                company=company, is_active=True
            )
        self.fields['branch'].required = False
        self.fields['address'].required = False
        self.fields['capacity'].required = False
        self.fields['notes'].required = False


class StockAdjustmentForm(forms.Form):
    ADJUSTMENT_TYPES = [
        ('add', 'Tambah Stok (+)'),
        ('reduce', 'Kurangi Stok (-)'),
    ]
    adjustment_type = forms.ChoiceField(
        choices=ADJUSTMENT_TYPES,
        widget=forms.RadioSelect(attrs={'class': 'form-radio'}),
        label='Tipe Adjustment',
    )
    quantity = forms.DecimalField(
        min_value=0.01,
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-input', 'step': '0.01', 'min': '0.01',
            'placeholder': '0',
        }),
        label='Jumlah',
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3,
                                     'placeholder': 'Alasan adjustment (wajib diisi)'}),
        label='Alasan / Keterangan',
    )
