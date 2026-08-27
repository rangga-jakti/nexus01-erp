"""
Management command: python manage.py setup_demo_data
Demo data realistis untuk PT Nexus Utama — distributor elektronik.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
import random


class Command(BaseCommand):
    help = 'Setup realistic demo data for Nexus-01 ERP'

    @transaction.atomic
    def handle(self, *args, **options):
        from organization.models import Company, Branch, Department
        from accounts.models import User
        from inventory.models import Product, ProductCategory, UnitOfMeasure, Warehouse, Stock
        from purchasing.models import (Supplier, PurchaseRequest, PurchaseRequestItem,
                                        PurchaseOrder, PurchaseOrderItem)
        from sales.models import (Customer, Quotation, QuotationItem,
                                   SalesOrder, SalesOrderItem)
        from finance.models import Invoice, Payment, Expense
        from hr.models import (Employee, JobPosition, WorkSchedule, Attendance,
                                LeaveType, LeaveBalance, LeaveRequest,
                                PayrollComponent, Payroll, PayrollDetail, PayrollItem)

        company = Company.objects.filter(is_active=True).first()
        branch = Branch.objects.filter(company=company).first()
        admin = User.objects.filter(is_superuser=True).first()

        if not company:
            self.stdout.write('❌ Run setup_nexus first.')
            return

        self.stdout.write(f'\n🏢 Setting up demo data for: {company.name}\n')
        today = timezone.now().date()

        # ── Departments ──────────────────────────────────────────────────
        self.stdout.write('🏗️  Creating departments...')
        depts = {}
        for name in ['Pembelian', 'Penjualan', 'Gudang & Logistik', 'Keuangan', 'IT & Admin']:
            d, _ = Department.objects.get_or_create(
                company=company, name=name,
                defaults={'code': name[:5].upper().replace(' ', '').replace('&', ''), 'is_active': True}
            )
            depts[name] = d
            self.stdout.write(f'   ✓ {name}')

        # ── Units of Measure ─────────────────────────────────────────────
        self.stdout.write('\n📏 Creating units of measure...')
        units = {}
        for code, name, symbol in [
            ('PCS','Pcs','pcs'), ('BOX','Box','box'), ('SET','Set','set'),
            ('UNIT','Unit','unit'), ('LUSIN','Lusin','lusin'), ('KG','Kilogram','kg'), ('MTR','Meter','mtr'),
        ]:
            u, _ = UnitOfMeasure.objects.get_or_create(
                company=company, code=code,
                defaults={'name': name, 'symbol': symbol, 'is_active': True}
            )
            units[code] = u
            self.stdout.write(f'   ✓ {name}')

        # ── Product Categories ────────────────────────────────────────────
        self.stdout.write('\n📦 Creating product categories...')
        cats = {}
        for name, code in [
            ('Laptop & Komputer','LAPTOP'), ('Aksesori Komputer','AKSESOR'),
            ('Jaringan & Kabel','NETWORK'), ('Penyimpanan','STORAGE'),
        ]:
            c, _ = ProductCategory.objects.get_or_create(
                company=company, code=code,
                defaults={'name': name, 'is_active': True}
            )
            cats[code] = c
            self.stdout.write(f'   ✓ {name}')

        # ── Warehouses ────────────────────────────────────────────────────
        self.stdout.write('\n🏭 Creating warehouses...')
        warehouses = {}
        for code, name, address in [
            ('GDG-JKT', 'Gudang Jakarta', 'Jl. Raya Bekasi KM 18, Jakarta Timur'),
            ('GDG-BDG', 'Gudang Bandung', 'Jl. Soekarno Hatta No. 45, Bandung'),
        ]:
            w, _ = Warehouse.objects.get_or_create(
                company=company, code=code,
                defaults={'name': name, 'address': address, 'branch': branch, 'is_active': True}
            )
            warehouses[code] = w
            self.stdout.write(f'   ✓ {name}')

        # ── Products ──────────────────────────────────────────────────────
        self.stdout.write('\n🛍️  Creating products...')
        products_data = [
            ('LPT-001','Laptop ASUS VivoBook 15 i5-12th','LAPTOP','UNIT',6500000,7800000,5),
            ('LPT-002','Laptop Lenovo IdeaPad Slim 3','LAPTOP','UNIT',5800000,6900000,5),
            ('LPT-003','Laptop Acer Aspire 5 Ryzen 5','LAPTOP','UNIT',6200000,7400000,5),
            ('AKS-001','Mouse Wireless Logitech M185','AKSESOR','PCS',85000,125000,20),
            ('AKS-002','Keyboard Mechanical Redragon K552','AKSESOR','PCS',280000,380000,10),
            ('AKS-003','Headset Gaming Rexus Vonix','AKSESOR','PCS',195000,280000,10),
            ('AKS-004','Webcam Logitech C310 HD','AKSESOR','PCS',420000,580000,10),
            ('AKS-005','USB Hub 7 Port Orico','AKSESOR','PCS',95000,145000,15),
            ('NET-001','Router WiFi TP-Link Archer AX23','NETWORK','UNIT',480000,650000,8),
            ('NET-002','Switch 8 Port TP-Link TL-SF1008D','NETWORK','UNIT',145000,220000,10),
            ('NET-003','Kabel LAN CAT6 per meter','NETWORK','MTR',8000,12000,100),
            ('NET-004','Patch Panel 24 Port AMP','NETWORK','UNIT',380000,520000,5),
            ('STR-001','SSD Kingston A400 480GB','STORAGE','PCS',420000,580000,10),
            ('STR-002','Flashdisk Sandisk 64GB USB 3.0','STORAGE','PCS',75000,110000,30),
            ('STR-003','External HDD WD Elements 1TB','STORAGE','PCS',680000,890000,8),
        ]
        products = {}
        for sku, name, cat_code, unit_code, pp, sp, min_s in products_data:
            p, _ = Product.objects.get_or_create(
                company=company, sku=sku,
                defaults={
                    'name': name, 'category': cats[cat_code], 'unit': units[unit_code],
                    'purchase_price': Decimal(str(pp)), 'selling_price': Decimal(str(sp)),
                    'minimum_stock': min_s, 'is_active': True,
                }
            )
            products[sku] = p
            self.stdout.write(f'   ✓ {sku} — {name}')

        # ── Initial Stock ─────────────────────────────────────────────────
        self.stdout.write('\n📊 Setting up initial stock...')
        stock_data = [
            ('LPT-001','GDG-JKT',12),('LPT-002','GDG-JKT',8),('LPT-003','GDG-JKT',10),
            ('AKS-001','GDG-JKT',85),('AKS-002','GDG-JKT',42),('AKS-003','GDG-JKT',38),
            ('AKS-004','GDG-JKT',25),('AKS-005','GDG-JKT',60),
            ('NET-001','GDG-JKT',18),('NET-002','GDG-JKT',30),('NET-003','GDG-JKT',500),
            ('NET-004','GDG-JKT',12),('STR-001','GDG-JKT',35),('STR-002','GDG-JKT',120),
            ('STR-003','GDG-JKT',20),
            ('LPT-001','GDG-BDG',5),('LPT-002','GDG-BDG',4),
            ('AKS-001','GDG-BDG',40),('AKS-002','GDG-BDG',20),
            ('STR-001','GDG-BDG',15),('STR-002','GDG-BDG',60),
        ]
        for sku, wh_code, qty in stock_data:
            stock, created = Stock.objects.get_or_create(
                company=company, product=products[sku], warehouse=warehouses[wh_code],
                defaults={'quantity': 0, 'is_active': True}
            )
            if created or stock.quantity == 0:
                stock.add_stock(Decimal(str(qty)), 'IN',
                                reference='INIT-STOCK', notes='Stok awal demo', user=admin)
                self.stdout.write(f'   ✓ {sku} @ {wh_code}: {qty}')

        # ── Suppliers ─────────────────────────────────────────────────────
        self.stdout.write('\n🏭 Creating suppliers...')
        suppliers = {}
        for code, name, phone, email, address, terms in [
            ('SUP-001','PT Mega Elektronik Indonesia','021-5551234','purchasing@megaelektronik.co.id','Jl. Hayam Wuruk No. 28, Jakarta Barat',30),
            ('SUP-002','CV Anugerah Komputer','022-4445678','order@anugerahkomputer.com','Jl. BKR No. 15, Bandung',14),
            ('SUP-003','PT Distribusi Teknologi Nusantara','021-7778901','sales@distekno.id','Jl. Mangga Dua Raya No. 8, Jakarta Utara',30),
            ('SUP-004','UD Maju Bersama Tech','031-3334567','info@majubersamatech.com','Jl. Rungkut Industri No. 22, Surabaya',21),
            ('SUP-005','PT Global IT Solution','021-8889012','procurement@globalit.co.id','Jl. TB Simatupang No. 55, Jakarta Selatan',45),
        ]:
            s, _ = Supplier.objects.get_or_create(
                company=company, code=code,
                defaults={'name': name, 'phone': phone, 'email': email,
                          'address': address, 'payment_terms_days': terms, 'is_active': True}
            )
            suppliers[code] = s
            self.stdout.write(f'   ✓ {name}')

        # ── Customers ─────────────────────────────────────────────────────
        self.stdout.write('\n👥 Creating customers...')
        customers = {}
        for code, name, contact, phone, email, city, terms, limit in [
            ('CUST-001','PT Abadi Jaya Teknologi','Budi Santoso','021-5557890','budi@abadijaya.co.id','Jakarta',30,50000000),
            ('CUST-002','CV Mitra Solusi IT','Dewi Kusuma','022-3334567','dewi@mitrasolusiit.com','Bandung',14,20000000),
            ('CUST-003','PT Karya Digital Indonesia','Ahmad Fauzi','021-6667890','ahmad@karyadigital.id','Jakarta',30,75000000),
            ('CUST-004','Toko Komputer Sejahtera','Rizky Pratama','022-8889012','rizky@tokokomputersejahtera.com','Bandung',7,10000000),
            ('CUST-005','PT Inovasi Teknologi Mandiri','Siti Rahayu','021-4445678','siti@inovasitek.co.id','Depok',30,30000000),
            ('CUST-006','Universitas Nusantara','Dr. Hendra Wijaya','021-3332211','procurement@univ-nusantara.ac.id','Jakarta',45,100000000),
            ('CUST-007','PT Sentosa Grup','Rina Wulandari','031-5556677','rina@sentosagrup.com','Surabaya',30,40000000),
            ('CUST-008','CV Berkah Elektronik','Doni Prasetyo','024-7778899','doni@berkahelektronik.com','Semarang',14,15000000),
        ]:
            c, _ = Customer.objects.get_or_create(
                company=company, code=code,
                defaults={'name': name, 'contact_person': contact, 'phone': phone,
                          'email': email, 'city': city,
                          'payment_terms_days': terms, 'credit_limit': Decimal(str(limit)),
                          'is_active': True}
            )
            customers[code] = c
            self.stdout.write(f'   ✓ {name}')

        # ── Purchase Requests ─────────────────────────────────────────────
        self.stdout.write('\n📋 Creating purchase requests...')

        def make_pr(number, title, status, dept_name, supplier_code, days_ago, items):
            pr, created = PurchaseRequest.objects.get_or_create(
                company=company, number=number,
                defaults={
                    'title': title, 'status': status,
                    'department': depts.get(dept_name),
                    'suggested_supplier': suppliers.get(supplier_code),
                    'required_date': today - timedelta(days=days_ago-14),
                    'created_by': admin, 'branch': branch,
                    'submitted_at': timezone.now() - timedelta(days=days_ago) if status != 'DRAFT' else None,
                    'approved_at': timezone.now() - timedelta(days=days_ago-1) if status == 'APPROVED' else None,
                }
            )
            if created:
                for sku, qty, price in items:
                    PurchaseRequestItem.objects.create(
                        pr=pr, product=products[sku],
                        quantity=Decimal(str(qty)), unit=products[sku].unit,
                        estimated_price=Decimal(str(price)),
                    )
            return pr

        pr1 = make_pr('PR/2026/08/001','Pengadaan Laptop untuk Tim Sales Q3','APPROVED','Penjualan','SUP-001',25,
            [('LPT-001',5,6500000),('LPT-002',3,5800000)])
        pr2 = make_pr('PR/2026/08/002','Restok Aksesori Komputer Agustus','APPROVED','Gudang & Logistik','SUP-002',20,
            [('AKS-001',50,85000),('AKS-002',20,280000),('AKS-005',30,95000)])
        pr3 = make_pr('PR/2026/08/003','Pengadaan Perangkat Jaringan Kantor Baru','PENDING','IT & Admin','SUP-003',10,
            [('NET-001',10,480000),('NET-002',15,145000),('NET-003',200,8000)])
        pr4 = make_pr('PR/2026/08/004','Pengadaan SSD dan Storage untuk Server','DRAFT','IT & Admin','SUP-005',5,
            [('STR-001',20,420000),('STR-003',10,680000)])
        pr5 = make_pr('PR/2026/08/005','Pengadaan Aksesori Meeting Room','REJECTED','Penjualan','SUP-002',15,
            [('AKS-003',10,195000),('AKS-004',5,420000)])
        self.stdout.write('   ✓ 5 Purchase Requests created')

        # ── Purchase Orders ───────────────────────────────────────────────
        self.stdout.write('\n🛒 Creating purchase orders...')

        def make_po(number, supplier_code, pr, status, days_ago, tax_rate, items):
            po, created = PurchaseOrder.objects.get_or_create(
                company=company, number=number,
                defaults={
                    'supplier': suppliers[supplier_code],
                    'pr': pr, 'status': status,
                    'order_date': today - timedelta(days=days_ago),
                    'expected_date': today - timedelta(days=days_ago-7),
                    'warehouse': warehouses['GDG-JKT'],
                    'branch': branch,
                    'tax_rate': Decimal(str(tax_rate)),
                    'created_by': admin,
                    'payment_terms': f'NET {suppliers[supplier_code].payment_terms_days}',
                }
            )
            if created:
                for sku, qty, price in items:
                    PurchaseOrderItem.objects.create(
                        po=po, product=products[sku],
                        quantity=Decimal(str(qty)), unit=products[sku].unit,
                        unit_price=Decimal(str(price)),
                    )
            return po

        po1 = make_po('PO/2026/08/001','SUP-001',pr1,'RECEIVED',23,11,
            [('LPT-001',5,6500000),('LPT-002',3,5800000)])
        po2 = make_po('PO/2026/08/002','SUP-002',pr2,'RECEIVED',18,11,
            [('AKS-001',50,85000),('AKS-002',20,280000),('AKS-005',30,95000)])
        po3 = make_po('PO/2026/08/003','SUP-003',pr3,'SENT',8,11,
            [('NET-001',10,480000),('NET-002',15,145000),('NET-003',200,8000)])
        self.stdout.write('   ✓ 3 Purchase Orders created')

        # ── Sales Orders ──────────────────────────────────────────────────
        self.stdout.write('\n💰 Creating sales orders...')

        def make_so(number, cust_code, status, days_ago, tax_rate, items):
            so, created = SalesOrder.objects.get_or_create(
                company=company, number=number,
                defaults={
                    'customer': customers[cust_code], 'status': status,
                    'order_date': today - timedelta(days=days_ago),
                    'expected_delivery_date': today - timedelta(days=days_ago-5),
                    'warehouse': warehouses['GDG-JKT'],
                    'branch': branch, 'tax_rate': Decimal(str(tax_rate)),
                    'created_by': admin,
                }
            )
            if created:
                for sku, qty, price in items:
                    SalesOrderItem.objects.create(
                        so=so, product=products[sku],
                        quantity=Decimal(str(qty)), unit=products[sku].unit,
                        unit_price=Decimal(str(price)),
                    )
            return so

        so1 = make_so('SO/2026/08/001','CUST-001','DELIVERED',20,11,
            [('LPT-001',3,7800000),('AKS-001',10,125000),('AKS-002',5,380000)])
        so2 = make_so('SO/2026/08/002','CUST-003','CONFIRMED',15,11,
            [('LPT-002',5,6900000),('STR-001',10,580000),('STR-002',20,110000)])
        so3 = make_so('SO/2026/08/003','CUST-006','CONFIRMED',10,0,
            [('LPT-001',10,7800000),('LPT-003',5,7400000),('NET-001',5,650000)])
        so4 = make_so('SO/2026/08/004','CUST-002','DRAFT',3,11,
            [('AKS-001',20,125000),('AKS-003',10,280000),('STR-002',30,110000)])
        self.stdout.write('   ✓ 4 Sales Orders created')

        # ── Invoices ──────────────────────────────────────────────────────
        self.stdout.write('\n🧾 Creating invoices...')

        def make_invoice(number, inv_type, so=None, po=None, customer=None, supplier=None,
                         status='ISSUED', days_ago=10, subtotal=0, tax=0):
            total = Decimal(str(subtotal)) + Decimal(str(tax))
            paid = total if status == 'PAID' else (total / 2 if status == 'PARTIAL' else Decimal('0'))
            inv, _ = Invoice.objects.get_or_create(
                company=company, number=number,
                defaults={
                    'invoice_type': inv_type,
                    'customer': customer, 'supplier': supplier,
                    'so': so, 'po': po, 'status': status,
                    'invoice_date': today - timedelta(days=days_ago),
                    'due_date': today - timedelta(days=days_ago-30),
                    'subtotal': Decimal(str(subtotal)),
                    'tax_amount': Decimal(str(tax)),
                    'total_amount': total,
                    'paid_amount': paid,
                    'created_by': admin,
                }
            )
            return inv

        inv1 = make_invoice('INV/2026/08/001','SALES', so=so1, customer=so1.customer,
                            status='PAID', days_ago=18, subtotal=27000000, tax=2970000)
        inv2 = make_invoice('INV/2026/08/002','SALES', so=so2, customer=so2.customer,
                            status='ISSUED', days_ago=13, subtotal=41700000, tax=4587000)
        inv3 = make_invoice('INV/2026/08/003','SALES', so=so3, customer=so3.customer,
                            status='ISSUED', days_ago=8, subtotal=118250000, tax=0)
        pinv1 = make_invoice('PINV/2026/08/001','PURCHASE', po=po1, supplier=po1.supplier,
                             status='PAID', days_ago=20, subtotal=59900000, tax=6589000)
        pinv2 = make_invoice('PINV/2026/08/002','PURCHASE', po=po2, supplier=po2.supplier,
                             status='PARTIAL', days_ago=15, subtotal=12500000, tax=1375000)
        self.stdout.write('   ✓ 5 Invoices created')

        # ── Payments ──────────────────────────────────────────────────────
        self.stdout.write('\n💳 Creating payments...')
        for number, invoice, amount, method, days_ago in [
            ('PAY/2026/08/001', inv1, inv1.total_amount, 'TRANSFER', 16),
            ('PAY/2026/08/002', pinv1, pinv1.total_amount, 'TRANSFER', 18),
            ('PAY/2026/08/003', pinv2, pinv2.total_amount / 2, 'TRANSFER', 10),
        ]:
            Payment.objects.get_or_create(
                company=company, number=number,
                defaults={
                    'invoice': invoice, 'amount': amount,
                    'payment_method': method,
                    'payment_date': today - timedelta(days=days_ago),
                    'status': 'CONFIRMED', 'created_by': admin,
                    'reference_number': f'TRF-{number[-6:]}',
                }
            )
        self.stdout.write('   ✓ 3 Payments created')

        # ── Expenses ──────────────────────────────────────────────────────
        self.stdout.write('\n💸 Creating expenses...')
        for number, title, cat, amount, status, days_ago in [
            ('EXP/2026/08/001','Biaya Pengiriman Barang Agustus W1','OPERATIONAL',850000,'APPROVED',25),
            ('EXP/2026/08/002','Langganan Internet Kantor Agustus','OPERATIONAL',1500000,'APPROVED',20),
            ('EXP/2026/08/003','ATK dan Perlengkapan Kantor','ADMINISTRATIVE',325000,'APPROVED',18),
            ('EXP/2026/08/004','Transport Marketing Visit ke Bandung','TRAVEL',450000,'PENDING',10),
            ('EXP/2026/08/005','Biaya Makan Rapat Tim Sales','ENTERTAINMENT',780000,'APPROVED',7),
            ('EXP/2026/08/006','Maintenance AC Gudang Jakarta','MAINTENANCE',1200000,'PENDING',5),
        ]:
            Expense.objects.get_or_create(
                company=company, number=number,
                defaults={
                    'title': title, 'category': cat,
                    'amount': Decimal(str(amount)), 'status': status,
                    'expense_date': today - timedelta(days=days_ago),
                    'department': depts.get('Keuangan'), 'created_by': admin,
                }
            )
            self.stdout.write(f'   ✓ {title}')

        # ── Employees ─────────────────────────────────────────────────────
        self.stdout.write('\n👤 Creating employees...')
        positions = {p.code: p for p in JobPosition.objects.filter(company=company)}
        schedule = WorkSchedule.objects.filter(company=company, code='NORMAL').first()

        employees = {}
        for emp_id, first, last, gender, bdate, pos_code, dept_name, salary, join, emp_status, tax, bank, acc, acc_name in [
            ('EMP-001','Budi','Santoso','M','1988-05-12','MGR','Penjualan',12000000,'2020-03-01','PERMANENT','K2','BCA','1234567890','Budi Santoso'),
            ('EMP-002','Dewi','Kusuma','F','1992-08-20','STAFF','Penjualan',6500000,'2021-06-15','PERMANENT','TK0','Mandiri','0987654321','Dewi Kusuma'),
            ('EMP-003','Ahmad','Fauzi','M','1990-03-15','SPV','Gudang & Logistik',8500000,'2019-09-01','PERMANENT','K1','BNI','1122334455','Ahmad Fauzi'),
            ('EMP-004','Siti','Rahayu','F','1995-11-28','ADMIN','Keuangan',5500000,'2022-01-10','PERMANENT','TK0','BCA','5544332211','Siti Rahayu'),
            ('EMP-005','Rizky','Pratama','M','1998-07-04','IT','IT & Admin',7000000,'2022-08-01','PERMANENT','TK0','Mandiri','9988776655','Rizky Pratama'),
        ]:
            emp, _ = Employee.objects.get_or_create(
                company=company, employee_id=emp_id,
                defaults={
                    'first_name': first, 'last_name': last, 'gender': gender,
                    'birth_date': date.fromisoformat(bdate),
                    'position': positions.get(pos_code),
                    'department': depts.get(dept_name),
                    'basic_salary': Decimal(str(salary)),
                    'join_date': date.fromisoformat(join),
                    'employment_status': emp_status, 'tax_status': tax,
                    'bank_name': bank, 'bank_account': acc, 'bank_account_name': acc_name,
                    'branch': branch, 'nationality': 'Indonesia',
                    'marital_status': 'MARRIED' if tax.startswith('K') else 'SINGLE',
                }
            )
            employees[emp_id] = emp
            self.stdout.write(f'   ✓ {emp_id} — {first} {last}')

        # ── Attendance ────────────────────────────────────────────────────
        self.stdout.write('\n📅 Creating attendance records...')
        for i in range(14, 0, -1):
            att_date = today - timedelta(days=i)
            if att_date.weekday() >= 5:
                continue
            for emp in employees.values():
                r = random.random()
                if r > 0.9:
                    status, ci, co, late = 'ABSENT', None, None, 0
                elif r > 0.75:
                    status, ci, co, late = 'LATE', '08:30', '17:00', 15
                else:
                    status, ci, co, late = 'PRESENT', '07:55', '17:05', 0
                Attendance.objects.get_or_create(
                    company=company, employee=emp, date=att_date,
                    defaults={'status': status, 'check_in': ci, 'check_out': co,
                              'late_minutes': late, 'schedule': schedule}
                )
        self.stdout.write('   ✓ Attendance 14 hari untuk 5 karyawan')

        # ── Leave Balances & Requests ─────────────────────────────────────
        self.stdout.write('\n🏖️  Creating leave data...')
        lt_tahunan = LeaveType.objects.filter(company=company, code='TAHUNAN').first()
        lt_sakit = LeaveType.objects.filter(company=company, code='SAKIT').first()
        if lt_tahunan:
            for emp in employees.values():
                LeaveBalance.objects.get_or_create(
                    company=company, employee=emp, leave_type=lt_tahunan, year=today.year,
                    defaults={'total_days': 12, 'used_days': random.randint(1, 5)}
                )
            emp1 = employees.get('EMP-001')
            emp2 = employees.get('EMP-002')
            if emp1:
                LeaveRequest.objects.get_or_create(
                    company=company, employee=emp1,
                    start_date=today + timedelta(days=5),
                    defaults={
                        'leave_type': lt_tahunan,
                        'end_date': today + timedelta(days=7),
                        'total_days': 3, 'reason': 'Liburan keluarga ke Yogyakarta',
                        'status': 'PENDING', 'created_by': admin,
                    }
                )
            if lt_sakit and emp2:
                LeaveRequest.objects.get_or_create(
                    company=company, employee=emp2,
                    start_date=today - timedelta(days=5),
                    defaults={
                        'leave_type': lt_sakit,
                        'end_date': today - timedelta(days=4),
                        'total_days': 2, 'reason': 'Sakit demam, ada surat dokter',
                        'status': 'APPROVED', 'approved_by': admin,
                        'approved_at': timezone.now() - timedelta(days=5),
                        'created_by': admin,
                    }
                )
        self.stdout.write('   ✓ Saldo cuti + 2 leave requests')

        # ── Payroll ───────────────────────────────────────────────────────
        self.stdout.write('\n💰 Creating payroll...')
        last_month = today.replace(day=1) - timedelta(days=1)
        payroll, created = Payroll.objects.get_or_create(
            company=company, period_month=last_month.month,
            period_year=last_month.year, branch=branch,
            defaults={
                'name': f'Gaji {last_month.strftime("%B %Y")}',
                'status': 'APPROVED',
                'payment_date': today.replace(day=1) - timedelta(days=1),
                'created_by': admin, 'approved_by': admin,
                'approved_at': timezone.now() - timedelta(days=2),
            }
        )

        if created:
            components = {c.code: c for c in PayrollComponent.objects.filter(company=company, is_active=True)}
            total_basic = total_earn = total_ded = total_net = Decimal('0')

            for emp in employees.values():
                detail = PayrollDetail.objects.create(
                    company=company, payroll=payroll, employee=emp,
                    basic_salary=emp.basic_salary,
                    present_days=random.randint(19, 22), leave_days=random.randint(0, 2),
                    absent_days=random.randint(0, 1), working_days=22,
                    overtime_minutes=random.randint(0, 120), late_minutes=random.randint(0, 30),
                )
                earnings = deductions = Decimal('0')
                for code in ['TJ_MAKAN', 'TJ_TRANSPORT']:
                    comp = components.get(code)
                    if comp:
                        amt = Decimal(str(comp.default_amount))
                        PayrollItem.objects.create(payroll_detail=detail, component=comp, amount=amt)
                        earnings += amt
                for code, pct in [('BPJS_KES_EMP', 1), ('BPJS_TK_JHT', 2), ('BPJS_TK_JP', 1)]:
                    comp = components.get(code)
                    if comp:
                        amt = emp.basic_salary * Decimal(str(pct)) / 100
                        PayrollItem.objects.create(payroll_detail=detail, component=comp, amount=amt)
                        deductions += amt
                gross = emp.basic_salary + earnings
                net = gross - deductions
                detail.total_earnings = earnings
                detail.total_deductions = deductions
                detail.gross_salary = gross
                detail.net_salary = net
                detail.save()
                total_basic += emp.basic_salary
                total_earn += earnings
                total_ded += deductions
                total_net += net

            payroll.total_basic_salary = total_basic
            payroll.total_earnings = total_earn
            payroll.total_deductions = total_ded
            payroll.total_net_salary = total_net
            payroll.employee_count = len(employees)
            payroll.save()
            self.stdout.write(f'   ✓ {payroll.name} — {len(employees)} karyawan, total Rp {total_net:,.0f}')

        self.stdout.write('\n' + '='*55)
        self.stdout.write('✅ Demo data setup complete!')
        self.stdout.write(f'   Produk   : {Product.objects.filter(company=company).count()} SKU')
        self.stdout.write(f'   Supplier : {Supplier.objects.filter(company=company).count()}')
        self.stdout.write(f'   Customer : {Customer.objects.filter(company=company).count()}')
        self.stdout.write(f'   PR       : {PurchaseRequest.objects.filter(company=company).count()}')
        self.stdout.write(f'   PO       : {PurchaseOrder.objects.filter(company=company).count()}')
        self.stdout.write(f'   SO       : {SalesOrder.objects.filter(company=company).count()}')
        self.stdout.write(f'   Invoice  : {Invoice.objects.filter(company=company).count()}')
        self.stdout.write(f'   Expense  : {Expense.objects.filter(company=company).count()}')
        self.stdout.write(f'   Karyawan : {Employee.objects.filter(company=company).count()}')
        self.stdout.write('='*55 + '\n')
        self.stdout.write('👉 Buka http://localhost:8888\n')
