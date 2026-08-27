path = '/app/core/views.py'
with open(path) as f:
    c = f.read()

c = c.replace(
    """        low_stock = Stock.objects.filter(
            company=company,
            quantity__lte=models.F('minimum_quantity'),
        ).count()""",
    """        from django.db.models import F
        low_stock = Stock.objects.filter(
            company=company,
            quantity__lte=F('product__minimum_stock'),
        ).count()"""
)

with open(path, 'w') as f:
    f.write(c)
print('done')
