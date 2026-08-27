from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from .models import Customer, Quotation, QuotationItem, SalesOrder, SalesOrderItem, Delivery, DeliveryItem


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['code','name','contact_person','email','phone','address','city','tax_id','payment_terms_days','credit_limit','notes']
    def __init__(self, *args, company=None, **kwargs):
        kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        for fname, field in self.fields.items():
            if isinstance(field.widget, forms.TextInput):
                field.widget.attrs['class'] = 'form-input'
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class': 'form-textarea', 'rows': 2})
            elif isinstance(field.widget, forms.NumberInput):
                field.widget.attrs['class'] = 'form-input'
        for fn in ['contact_person','email','phone','address','city','tax_id','notes','credit_limit']:
            self.fields[fn].required = False


class QuotationForm(forms.ModelForm):
    class Meta:
        model = Quotation
        fields = ['customer','branch','valid_until','tax_rate','discount_amount','notes','terms_conditions']
        widgets = {
            'customer': forms.Select(attrs={'class':'form-select'}),
            'branch': forms.Select(attrs={'class':'form-select'}),
            'valid_until': forms.DateInput(attrs={'class':'form-input','type':'date'}),
            'tax_rate': forms.NumberInput(attrs={'class':'form-input','step':'0.01','min':'0'}),
            'discount_amount': forms.NumberInput(attrs={'class':'form-input','step':'1','min':'0'}),
            'notes': forms.Textarea(attrs={'class':'form-textarea','rows':2}),
            'terms_conditions': forms.Textarea(attrs={'class':'form-textarea','rows':3}),
        }
    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            from organization.models import Branch
            self.fields['customer'].queryset = Customer.objects.filter(company=company, is_active=True)
            self.fields['branch'].queryset = Branch.objects.filter(company=company, is_active=True)
        for f in ['branch','valid_until','notes','terms_conditions','discount_amount']:
            self.fields[f].required = False


class QuotationItemForm(forms.ModelForm):
    class Meta:
        model = QuotationItem
        fields = ['product','description','quantity','unit','unit_price','discount_percent']
        widgets = {
            'product': forms.Select(attrs={'class':'form-select text-sm'}),
            'description': forms.TextInput(attrs={'class':'form-input text-sm'}),
            'quantity': forms.NumberInput(attrs={'class':'form-input text-sm','step':'0.01','min':'0.01','placeholder':'0'}),
            'unit': forms.Select(attrs={'class':'form-select text-sm'}),
            'unit_price': forms.NumberInput(attrs={'class':'form-input text-sm','step':'1','min':'0','placeholder':'0'}),
            'discount_percent': forms.NumberInput(attrs={'class':'form-input text-sm','step':'0.01','min':'0','max':'100','placeholder':'0'}),
        }
    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            from inventory.models import Product, UnitOfMeasure
            self.fields['product'].queryset = Product.objects.filter(company=company, is_active=True)
            self.fields['unit'].queryset = UnitOfMeasure.objects.filter(company=company, is_active=True)
        self.fields['description'].required = False
        self.fields['unit'].required = False
        self.fields['discount_percent'].required = False


class QuotItemFormSet(BaseInlineFormSet):
    pass


QuotationItemFormSet = inlineformset_factory(
    Quotation, QuotationItem,
    form=QuotationItemForm,
    formset=QuotItemFormSet,
    extra=3, can_delete=True, min_num=1, validate_min=True,
)


class SalesOrderForm(forms.ModelForm):
    class Meta:
        model = SalesOrder
        fields = ['customer','branch','warehouse','expected_delivery_date','shipping_address','tax_rate','discount_amount','notes']
        widgets = {
            'customer': forms.Select(attrs={'class':'form-select'}),
            'branch': forms.Select(attrs={'class':'form-select'}),
            'warehouse': forms.Select(attrs={'class':'form-select'}),
            'expected_delivery_date': forms.DateInput(attrs={'class':'form-input','type':'date'}),
            'shipping_address': forms.Textarea(attrs={'class':'form-textarea','rows':2}),
            'tax_rate': forms.NumberInput(attrs={'class':'form-input','step':'0.01'}),
            'discount_amount': forms.NumberInput(attrs={'class':'form-input','step':'1','min':'0'}),
            'notes': forms.Textarea(attrs={'class':'form-textarea','rows':2}),
        }
    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            from organization.models import Branch
            from inventory.models import Warehouse
            self.fields['customer'].queryset = Customer.objects.filter(company=company, is_active=True)
            self.fields['branch'].queryset = Branch.objects.filter(company=company, is_active=True)
            self.fields['warehouse'].queryset = Warehouse.objects.filter(company=company, is_active=True)
        for f in ['branch','warehouse','expected_delivery_date','shipping_address','notes','discount_amount']:
            self.fields[f].required = False


class DeliveryForm(forms.ModelForm):
    class Meta:
        model = Delivery
        fields = ['warehouse','delivery_date','shipping_method','tracking_number','notes']
        widgets = {
            'warehouse': forms.Select(attrs={'class':'form-select'}),
            'delivery_date': forms.DateInput(attrs={'class':'form-input','type':'date'}),
            'shipping_method': forms.TextInput(attrs={'class':'form-input','placeholder':'e.g. JNE, Gojek, Kurir Internal'}),
            'tracking_number': forms.TextInput(attrs={'class':'form-input'}),
            'notes': forms.Textarea(attrs={'class':'form-textarea','rows':2}),
        }
    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            from inventory.models import Warehouse
            self.fields['warehouse'].queryset = Warehouse.objects.filter(company=company, is_active=True)
        for f in ['delivery_date','shipping_method','tracking_number','notes']:
            self.fields[f].required = False
