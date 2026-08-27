# PostgreSQL Setup — Nexus-01 ERP

## 1. Install PostgreSQL (Windows)

Bang udah punya PostgreSQL di PATH (`D:\Program Files\PostgreSQL\16\bin`) — skip install.

## 2. Buat database & user

Buka PowerShell **as Administrator**, lalu:

```powershell
# Masuk ke psql sebagai superuser
psql -U postgres
```

Di dalam psql, jalankan:

```sql
-- Buat database
CREATE DATABASE nexus01_db
    WITH ENCODING='UTF8'
    LC_COLLATE='Indonesian_Indonesia.1252'
    LC_CTYPE='Indonesian_Indonesia.1252'
    TEMPLATE=template0;

-- Atau pakai encoding universal kalau yang atas error:
-- CREATE DATABASE nexus01_db WITH ENCODING='UTF8' TEMPLATE=template0;

-- Buat user khusus
CREATE USER nexus01_user WITH PASSWORD 'nexus2024_pg!';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE nexus01_db TO nexus01_user;

-- Untuk PostgreSQL 15+, perlu ini juga:
\c nexus01_db
GRANT ALL ON SCHEMA public TO nexus01_user;

-- Keluar
\q
```

## 3. Update file .env

Edit `D:\Projects\nexus01\.env`:

```env
# Django
SECRET_KEY=your-secret-key-dari-file-lama
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database PostgreSQL
DB_NAME=nexus01_db
DB_USER=nexus01_user
DB_PASSWORD=nexus2024_pg!
DB_HOST=localhost
DB_PORT=5432

COMPANY_NAME=Nexus-01 ERP
```

## 4. Update settings.py — ganti SQLite ke PostgreSQL

Edit `D:\Projects\nexus01\nexus01\settings.py`.

Cari bagian:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

Ganti dengan:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='nexus01_db'),
        'USER': config('DB_USER', default='nexus01_user'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'OPTIONS': {
            'connect_timeout': 10,
        },
    }
}
```

## 5. Migrate & setup ulang

```powershell
cd "D:\Projects\nexus01"
venv\Scripts\activate

# Test koneksi dulu
python manage.py dbshell

# Kalau berhasil masuk psql, keluar lagi: \q
# Lalu migrate
python manage.py migrate
python manage.py setup_nexus
python manage.py runserver
```

## 6. Troubleshooting

### Error: password authentication failed
```powershell
# Reset password user di psql
psql -U postgres -c "ALTER USER nexus01_user WITH PASSWORD 'nexus2024_pg!';"
```

### Error: database does not exist  
```powershell
psql -U postgres -c "CREATE DATABASE nexus01_db OWNER nexus01_user;"
```

### Error: could not connect to server
Pastikan PostgreSQL service running:
```powershell
# Cek status
Get-Service postgresql*

# Start kalau mati
Start-Service postgresql-x64-16
```

### Error: SSL connection required
Tambahkan ke OPTIONS di settings.py:
```python
'OPTIONS': {
    'sslmode': 'disable',
    'connect_timeout': 10,
}
```

## 7. Perbedaan SQLite vs PostgreSQL di Nexus-01

| Fitur | SQLite | PostgreSQL |
|-------|--------|------------|
| Cocok untuk | Development | Production |
| Concurrent users | ❌ Terbatas | ✅ Ribuan |
| Full-text search | ❌ Basic | ✅ Native |
| JSON queries | ❌ Terbatas | ✅ Powerful |
| Backup | Copy file | pg_dump |
| Performance | OK untuk dev | Jauh lebih cepat |

Untuk portfolio, SQLite sudah cukup ditunjukkan. PostgreSQL wajib kalau mau deploy ke production/VPS.
