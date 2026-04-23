#!/bin/bash
set -e

echo "[entrypoint] Waiting for PostgreSQL..."
until pg_isready -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "${DB_USER:-postgres}" -q; do
    sleep 1
done
echo "[entrypoint] PostgreSQL ready."

echo "[entrypoint] Running migrations..."
alembic upgrade heads

echo "[entrypoint] Seeding initial data..."
python seed_data.py

echo "[entrypoint] Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
