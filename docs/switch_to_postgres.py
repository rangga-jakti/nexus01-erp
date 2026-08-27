"""
Script helper: python docs/switch_to_postgres.py
Otomatis update settings.py dari SQLite ke PostgreSQL.
Jalankan dari folder D:\Projects\nexus01
"""
import re
import sys
import os

settings_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'nexus01', 'settings.py')

with open(settings_path) as f:
    content = f.read()

sqlite_block = """DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}"""

postgres_block = """DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='nexus01_db'),
        'USER': config('DB_USER', default='nexus01_user'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'OPTIONS': {
            'connect_timeout': 10,
            'sslmode': 'disable',
        },
    }
}"""

if sqlite_block in content:
    content = content.replace(sqlite_block, postgres_block)
    with open(settings_path, 'w') as f:
        f.write(content)
    print("✅ settings.py berhasil diupdate ke PostgreSQL!")
    print("📝 Sekarang edit .env dan isi DB_NAME, DB_USER, DB_PASSWORD")
    print("🚀 Lalu jalankan: python manage.py migrate && python manage.py setup_nexus")
elif 'postgresql' in content:
    print("ℹ️  settings.py sudah pakai PostgreSQL.")
else:
    print("⚠️  Tidak bisa menemukan DATABASES block. Edit manual di nexus01/settings.py")
