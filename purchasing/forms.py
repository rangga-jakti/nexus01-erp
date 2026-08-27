from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from .models import Supplier, PurchaseRequest, PurchaseRequestItem, PurchaseOrder, PurchaseOrderItem, GoodsReceipt, GoodsReceiptItem


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['code','name','legal_name','tax_id','contact_person','email','phone','website','address','city','payment_terms_days','notes']
        widgets = { f: forms.TextInput(attrs={'class':'form-input'}) for f in ['code','name','legal_name','tax_id','contact_person','email','phone','website','city'] }
    def __init__(self, *args, **kwargs):
        kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        self.fields['address'].widget = forms.Textarea(attrs={'class':'form-textarea','rows':2})
        self.fields['notes'].widget = forms.Textarea(attrs={'class':'form-textarea','rows':2})
        self.fields['payment_terms_days'].widget = forms.NumberInput(attrs={'class':'form-input','min':'0'})
        for f in ['legal_name','tax_id','contact_person','email','phone','website','address','city','notes']:
            self.fields[f].required = False


class PurchaseRequestForm(forms.ModelForm):
    class Meta:
        model = PurchaseRequest
        fields = ['title','branch','department','suggested_supplier','required_date','notes']
        widgets = {
            'title': forms.TextInput(attrs={'class':'form-input','placeholder':'Deskripsi singkat kebutuhan'}),
            'branch': forms.Select(attrs={'class':'form-select'}),
            'department': forms.Select(attrs={'class':'form-select'}),
            'suggested_supplier': forms.Select(attrs={'class':'form-select'}),
            'required_date': forms.DateInput(attrs={'class':'form-input','type':'date'}),
            'notes': forms.Textarea(attrs={'class':'form-textarea','rows':3}),
        }
    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            from organization.models import Branch, Department
            self.fields['branch'].queryset = Branch.objects.filter(company=company, is_active=True)
            self.fields['department'].queryset = Department.objects.filter(company=company, is_active=True)
            self.fields['suggested_supplier'].queryset = Supplier.objects.filter(company=company, is_active=True)
        for f in ['branch','department','suggested_supplier','required_date','notes']:
            self.fields[f].required = False


class PurchaseRequestItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseRequestItem
        fields = ['product','description','quantity','unit','estimated_price','notes']
        widgets = {
            'product': forms.Select(attrs={'class':'form-select text-sm'}),
            'description': forms.TextInput(attrs={'class':'form-input text-sm','placeholder':'Atau tulis deskripsi manual'}),
            'quantity': forms.NumberInput(attrs={'class':'form-input text-sm','step':'0.01','min':'0.01','placeholder':'0'}),
            'unit': forms.Select(attrs={'class':'form-select text-sm'}),
            'estimated_price': forms.NumberInput(attrs={'class':'form-input text-sm','step':'1','min':'0','placeholder':'0'}),
            'notes': forms.TextInput(attrs={'class':'form-input text-sm','placeholder':'Catatan (opsional)'}),
        }
    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            from inventory.models import Product, UnitOfMeasure
            self.fields['product'].queryset = Product.objects.filter(company=company, is_active=True)
            self.fields['unit'].queryset = UnitOfMeasure.objects.filter(company=company, is_active=True)
        self.fields['product'].required = False
        self.fields['description'].required = False
        self.fields['unit'].required = False
        self.fields['estimated_price'].required = False
        self.fields['notes'].required = False


class PRItemFormSet(BaseInlineFormSet):
    """Custom FormSet yang support company kwarg via form_kwargs."""
    pass


PurchaseRequestItemFormSet = inlineformset_factory(
    PurchaseRequest, PurchaseRequestItem,
    form=PurchaseRequestItemForm,
    formset=PRItemFormSet,
    extra=3, can_delete=True, min_num=1, validate_min=True,
)


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['supplier','branch','warehouse','expected_date','payment_terms','shipping_address','tax_rate','discount_amount','notes','supplier_reference']
        widgets = {
            'supplier': forms.Select(attrs={'class':'form-select'}),
            'branch': forms.Select(attrs={'class':'form-select'}),
            'warehouse': forms.Select(attrs={'class':'form-select'}),
            'expected_date': forms.DateInput(attrs={'class':'form-input','type':'date'}),
            'payment_terms': forms.TextInput(attrs={'class':'form-input','placeholder':'e.g. NET 30'}),
            'shipping_address': forms.Textarea(attrs={'class':'form-textarea','rows':2}),
            'tax_rate': forms.NumberInput(attrs={'class':'form-input','step':'0.01','min':'0'}),
            'discount_amount': forms.NumberInput(attrs={'class':'form-input','step':'1','min':'0'}),
            'notes': forms.Textarea(attrs={'class':'form-textarea','rows':2}),
            'supplier_reference': forms.TextInput(attrs={'class':'form-input','placeholder':'No. PO dari supplier'}),
        }
    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            from organization.models import Branch
            from inventory.models import Warehouse
            self.fields['supplier'].queryset = Supplier.objects.filter(company=company, is_active=True)
            self.fields['branch'].queryset = Branch.objects.filter(company=company, is_active=True)
            self.fields['warehouse'].queryset = Warehouse.objects.filter(company=company, is_active=True)
        for f in ['branch','warehouse','expected_date','payment_terms','shipping_address','notes','supplier_reference','discount_amount']:
            self.fields[f].required = False


class GoodsReceiptForm(forms.ModelForm):
    class Meta:
        model = GoodsReceipt
        fields = ['warehouse','delivery_note','notes']
        widgets = {
            'warehouse': forms.Select(attrs={'class':'form-select'}),
            'delivery_note': forms.TextInput(attrs={'class':'form-input','placeholder':'Nomor surat jalan dari supplier'}),
            'notes': forms.Textarea(attrs={'class':'form-textarea','rows':2}),
        }
    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            from inventory.models import Warehouse
            self.fields['warehouse'].queryset = Warehouse.objects.filter(company=company, is_active=True)
        self.fields['delivery_note'].required = False
        self.fields['notes'].required = False
