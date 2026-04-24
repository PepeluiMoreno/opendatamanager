#!/bin/bash
set -e

echo "[entrypoint] Waiting for PostgreSQL..."
until pg_isready -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "${DB_USER:-postgres}" -q; do
    sleep 1
done
echo "[entrypoint] PostgreSQL ready."

echo "[entrypoint] Running migrations..."

python - <<'PYEOF'
import os
from sqlalchemy import create_engine, text
engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as conn:
    conn.execute(text("CREATE SCHEMA IF NOT EXISTS opendata"))
    conn.execute(text("DROP TABLE IF EXISTS opendata.alembic_version"))
    conn.commit()
PYEOF

alembic upgrade heads

echo "[entrypoint] Seeding fetcher catalog..."
python seed_fetchers.py || echo "[entrypoint] WARNING: seed_fetchers.py failed — app arranca igualmente."

echo "[entrypoint] Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
