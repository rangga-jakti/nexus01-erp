"""
Management command: python manage.py setup_nexus

Jalankan ini sekali setelah migrate pertama untuk:
1. Buat semua Permission bawaan sistem
2. Buat Role default (Super Admin, Admin, Manager, Staff, Viewer)
3. Setup company pertama
4. Buat superuser pertama

Ini pengganti fixtures — lebih mudah di-maintain dan bisa di-rerun safely.
"""

from django.core.management.base import BaseCommand
from django.db import transaction


PERMISSIONS = [
    # Format: (code, name, module)
    # Accounts
    ('accounts.view_user', 'Lihat User', 'accounts'),
    ('accounts.create_user', 'Buat User', 'accounts'),
    ('accounts.edit_user', 'Edit User', 'accounts'),
    ('accounts.delete_user', 'Hapus User', 'accounts'),
    ('accounts.manage_roles', 'Kelola Role & Permission', 'accounts'),
    ('accounts.manage_user_companies', 'Kelola User per Company', 'accounts'),

    # Organization
    ('org.view_company', 'Lihat Company', 'organization'),
    ('org.edit_company', 'Edit Company', 'organization'),
    ('org.manage_branch', 'Kelola Branch', 'organization'),
    ('org.manage_department', 'Kelola Department', 'organization'),

    # Inventory
    ('inventory.view_product', 'Lihat Produk', 'inventory'),
    ('inventory.create_product', 'Buat Produk', 'inventory'),
    ('inventory.edit_product', 'Edit Produk', 'inventory'),
    ('inventory.delete_product', 'Hapus Produk', 'inventory'),
    ('inventory.view_stock', 'Lihat Stok', 'inventory'),
    ('inventory.adjust_stock', 'Adjust Stok Manual', 'inventory'),
    ('inventory.view_warehouse', 'Lihat Gudang', 'inventory'),
    ('inventory.manage_warehouse', 'Kelola Gudang', 'inventory'),

    # Purchasing
    ('purchasing.view_pr', 'Lihat Purchase Request', 'purchasing'),
    ('purchasing.create_pr', 'Buat Purchase Request', 'purchasing'),
    ('purchasing.approve_pr', 'Approve Purchase Request', 'purchasing'),
    ('purchasing.view_po', 'Lihat Purchase Order', 'purchasing'),
    ('purchasing.create_po', 'Buat Purchase Order', 'purchasing'),
    ('purchasing.approve_po', 'Approve Purchase Order', 'purchasing'),
    ('purchasing.view_goods_receipt', 'Lihat Goods Receipt', 'purchasing'),
    ('purchasing.create_goods_receipt', 'Buat Goods Receipt', 'purchasing'),
    ('purchasing.manage_supplier', 'Kelola Supplier', 'purchasing'),

    # Sales
    ('sales.view_quotation', 'Lihat Quotation', 'sales'),
    ('sales.create_quotation', 'Buat Quotation', 'sales'),
    ('sales.view_so', 'Lihat Sales Order', 'sales'),
    ('sales.create_so', 'Buat Sales Order', 'sales'),
    ('sales.approve_so', 'Approve Sales Order', 'sales'),
    ('sales.view_delivery', 'Lihat Delivery', 'sales'),
    ('sales.manage_customer', 'Kelola Customer', 'sales'),

    # Finance
    ('finance.view_invoice', 'Lihat Invoice', 'finance'),
    ('finance.create_invoice', 'Buat Invoice', 'finance'),
    ('finance.approve_invoice', 'Approve Invoice', 'finance'),
    ('finance.view_payment', 'Lihat Payment', 'finance'),
    ('finance.create_payment', 'Buat Payment', 'finance'),
    ('finance.approve_payment', 'Approve Payment', 'finance'),
    ('finance.view_expense', 'Lihat Expense', 'finance'),
    ('finance.create_expense', 'Buat Expense', 'finance'),
    ('finance.approve_expense', 'Approve Expense', 'finance'),

    # Reports
    ('reports.view_sales_report', 'Lihat Laporan Sales', 'reports'),
    ('reports.view_inventory_report', 'Lihat Laporan Inventory', 'reports'),
    ('reports.view_finance_report', 'Lihat Laporan Keuangan', 'reports'),
    ('reports.export_report', 'Export Laporan', 'reports'),

    # Core
    ('core.view_audit_log', 'Lihat Audit Log', 'core'),
    ('core.view_approval', 'Lihat Approval', 'core'),
    ('core.manage_approval', 'Kelola Approval', 'core'),
]


ROLES = [
    {
        'name': 'Super Admin',
        'code': 'super_admin',
        'description': 'Akses penuh ke semua fitur di semua modul.',
        'is_system': True,
        'all_permissions': True,
    },
    {
        'name': 'Admin',
        'code': 'admin',
        'description': 'Akses penuh kecuali pengaturan sistem sensitif.',
        'is_system': True,
        'permissions': [p[0] for p in PERMISSIONS if not p[0].startswith('core.view_audit')],
    },
    {
        'name': 'Finance Manager',
        'code': 'finance_manager',
        'description': 'Full akses finance, view inventory dan purchasing.',
        'is_system': True,
        'permissions': [
            p[0] for p in PERMISSIONS
            if p[2] in ('finance', 'reports') or p[0] in (
                'inventory.view_stock', 'inventory.view_product',
                'purchasing.view_pr', 'purchasing.view_po',
                'purchasing.approve_pr', 'purchasing.approve_po',
                'sales.view_so', 'sales.view_quotation',
            )
        ],
    },
    {
        'name': 'Warehouse Staff',
        'code': 'warehouse_staff',
        'description': 'Kelola inventory dan goods receipt.',
        'is_system': True,
        'permissions': [
            p[0] for p in PERMISSIONS
            if p[2] == 'inventory' or p[0] in (
                'purchasing.view_po', 'purchasing.create_goods_receipt',
                'purchasing.view_goods_receipt',
            )
        ],
    },
    {
        'name': 'Sales Staff',
        'code': 'sales_staff',
        'description': 'Kelola quotation, sales order, dan customer.',
        'is_system': True,
        'permissions': [
            p[0] for p in PERMISSIONS
            if p[2] == 'sales' or p[0] in (
                'inventory.view_stock', 'inventory.view_product',
                'reports.view_sales_report',
            )
        ],
    },
    {
        'name': 'Viewer',
        'code': 'viewer',
        'description': 'Hanya bisa melihat, tidak bisa membuat atau mengubah data.',
        'is_system': True,
        'permissions': [p[0] for p in PERMISSIONS if 'view_' in p[0]],
    },
]


class Command(BaseCommand):
    help = 'Setup initial Nexus-01 data: permissions, roles, company, superuser'

    def add_arguments(self, parser):
        parser.add_argument(
            '--company-name', default='PT Nexus Utama',
            help='Nama company pertama (default: PT Nexus Utama)'
        )
        parser.add_argument(
            '--admin-email', default='admin@nexus01.local',
            help='Email superuser pertama'
        )
        parser.add_argument(
            '--admin-password', default='nexus2024!',
            help='Password superuser pertama'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        from accounts.models import Permission as NexusPerm, Role, RolePermission, User, UserCompany
        from organization.models import Company, Branch

        self.stdout.write('\n🚀 Setting up Nexus-01...\n')

        # 1. Buat semua permissions
        self.stdout.write('📋 Creating permissions...')
        perm_objects = {}
        for code, name, module in PERMISSIONS:
            perm, created = NexusPerm.objects.get_or_create(
                code=code,
                defaults={'name': name, 'module': module}
            )
            perm_objects[code] = perm
            if created:
                self.stdout.write(f'   ✓ {code}')

        self.stdout.write(f'   → {len(perm_objects)} permissions ready')

        # 2. Buat semua roles
        self.stdout.write('\n👥 Creating roles...')
        role_objects = {}
        for role_data in ROLES:
            role, created = Role.objects.get_or_create(
                code=role_data['code'],
                defaults={
                    'name': role_data['name'],
                    'description': role_data['description'],
                    'is_system': role_data['is_system'],
                }
            )
            role_objects[role_data['code']] = role

            # Assign permissions
            if role_data.get('all_permissions'):
                perms_to_assign = list(perm_objects.values())
            else:
                perms_to_assign = [
                    perm_objects[code]
                    for code in role_data.get('permissions', [])
                    if code in perm_objects
                ]

            # Clear dan re-assign (idempotent)
            RolePermission.objects.filter(role=role).delete()
            RolePermission.objects.bulk_create([
                RolePermission(role=role, permission=perm)
                for perm in perms_to_assign
            ])

            action = 'created' if created else 'updated'
            self.stdout.write(f'   ✓ {role.name} ({len(perms_to_assign)} permissions) — {action}')

        # 3. Buat company pertama
        self.stdout.write('\n🏢 Creating company...')
        company, created = Company.objects.get_or_create(
            code='NEXUS',
            defaults={
                'name': options['company_name'],
                'legal_name': options['company_name'],
                'country': 'Indonesia',
                'currency': 'IDR',
            }
        )
        action = 'created' if created else 'already exists'
        self.stdout.write(f'   ✓ {company} — {action}')

        # Buat HQ branch
        branch, _ = Branch.objects.get_or_create(
            company=company,
            code='HQ',
            defaults={
                'name': 'Kantor Pusat',
                'is_headquarters': True,
            }
        )
        self.stdout.write(f'   ✓ Branch: {branch.name}')

        # 4. Buat superuser
        self.stdout.write('\n👤 Creating superuser...')
        admin_email = options['admin_email']
        if not User.objects.filter(email=admin_email).exists():
            admin = User.objects.create_superuser(
                username='admin',
                email=admin_email,
                password=options['admin_password'],
                first_name='Super',
                last_name='Admin',
                is_verified=True,
            )
            # Assign ke company dengan role Super Admin
            UserCompany.objects.create(
                user=admin,
                company=company,
                role=role_objects['super_admin'],
                is_default=True,
                is_active=True,
            )
            self.stdout.write(f'   ✓ Superuser created: {admin_email}')
            self.stdout.write(f'   ✓ Password: {options["admin_password"]}')
        else:
            self.stdout.write(f'   → Superuser {admin_email} already exists')

        self.stdout.write('\n' + '='*50)
        self.stdout.write('✅ Nexus-01 setup complete!')
        self.stdout.write(f'   URL: http://localhost:8000')
        self.stdout.write(f'   Admin: http://localhost:8000/admin')
        self.stdout.write(f'   Login: {options["admin_email"]} / {options["admin_password"]}')
        self.stdout.write('='*50 + '\n')
