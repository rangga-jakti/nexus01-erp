#!/bin/bash
set -e

echo "🚀 Starting Nexus-01 ERP..."

# Wait for PostgreSQL
echo "⏳ Waiting for PostgreSQL..."
while ! python -c "
import psycopg2, os
psycopg2.connect(
    dbname=os.environ.get('DB_NAME', 'nexus01_db'),
    user=os.environ.get('DB_USER', 'nexus01_user'),
    password=os.environ.get('DB_PASSWORD', ''),
    host=os.environ.get('DB_HOST', 'db'),
    port=os.environ.get('DB_PORT', '5432'),
)
" 2>/dev/null; do
    echo "  PostgreSQL not ready, retrying in 2s..."
    sleep 2
done
echo "✅ PostgreSQL ready!"

# Run migrations
echo "📦 Running migrations..."
python manage.py migrate --noinput

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# Setup initial data jika belum ada
echo "⚙️  Running setup..."
python manage.py setup_nexus || true
python manage.py setup_hr || true

# Start server
echo "🌐 Starting server on port 8000..."
exec python manage.py runserver 0.0.0.0:8000
