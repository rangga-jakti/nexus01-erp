# Nexus-01 ERP

> Sistem ERP modular berbasis Django untuk manajemen operasional bisnis multi-company.

## Stack

| Layer | Teknologi |
|-------|-----------|
| Backend | Django 5.1.4 |
| Database | PostgreSQL (SQLite untuk dev) |
| Frontend | HTMX + Tailwind CSS + Alpine.js |
| Icons | Tabler Icons |

## Modul

- **Core** — Audit log, Approval engine, Notifications
- **Accounts** — Custom User, RBAC (Role + Permission), UserCompany
- **Organization** — Company, Branch, Department (multi-company/multi-branch)
- **Inventory** — Product, Warehouse, Stock, StockMovement
- **Purchasing** — Supplier, PurchaseRequest, PurchaseOrder, GoodsReceipt
- **Sales** — Customer, Quotation, SalesOrder, Delivery
- **Finance** — Invoice, Payment, Expense
- **Reports** — Dashboard & laporan lintas modul

## Quick Start

```bash
# 1. Clone & setup environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Config environment
cp .env.example .env
# Edit .env — isi SECRET_KEY, DB credentials

# 3. Database setup
python manage.py migrate

# 4. Setup initial data (permissions, roles, company, superuser)
python manage.py setup_nexus

# 5. Run
python manage.py runserver
```

**Default login:** `admin` / `nexus2024!`

## Arsitektur

```
nexus01/
├── core/              # Shared: AuditLog, ApprovalRequest, Notification
├── accounts/          # User, Role, Permission, UserCompany
├── organization/      # Company, Branch, Department
├── inventory/         # Product, Warehouse, Stock, StockMovement
├── purchasing/        # Supplier, PR, PO, GoodsReceipt
├── sales/             # Customer, Quotation, SO, Delivery
├── finance/           # Invoice, Payment, Expense
├── reports/           # Aggregated reports
├── templates/         # Django templates (HTMX-ready)
└── static/            # CSS, JS, images
```

## Business Flow — Pembelian Barang

```
Purchase Request (DRAFT)
  → submit_for_approval()
  → ApprovalRequest (PENDING) → notifikasi ke Manager
  → Manager approve()
  → Purchase Request (APPROVED)
  → Purchase Order dibuat
  → Goods Receipt dikonfirmasi
  → Stock bertambah (StockMovement: PURCHASE_RECEIPT)
  → Invoice dibuat
  → Payment dikonfirmasi
```

## RBAC

| Role | Modul akses |
|------|-------------|
| Super Admin | Semua (50 permissions) |
| Admin | Semua kecuali audit log sensitif |
| Finance Manager | Finance + view Inventory/Purchasing |
| Warehouse Staff | Inventory + Goods Receipt |
| Sales Staff | Sales + view Inventory |
| Viewer | Semua (read-only) |

Satu user bisa punya role berbeda di company berbeda via `UserCompany`.

## Deployment (Production)

```bash
# Ganti SQLite → PostgreSQL di .env
DB_NAME=nexus01_db
DB_USER=nexus01_user
DB_PASSWORD=...
DB_HOST=localhost

# Collect static
python manage.py collectstatic

# Jalankan dengan Gunicorn
gunicorn nexus01.wsgi:application --bind 0.0.0.0:8000
```
