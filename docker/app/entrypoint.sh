#!/bin/bash
set -e

echo "[entrypoint] Waiting for PostgreSQL..."
until pg_isready -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "${DB_USER:-postgres}" -q; do
    sleep 1
done
echo "[entrypoint] PostgreSQL ready."

echo "[entrypoint] Running migrations..."

echo "[entrypoint] Reconciliando estado de migraciones..."
NEED_STAMP=$(python - <<'PYEOF'
import os
from sqlalchemy import create_engine, text, inspect
engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as conn:
    conn.execute(text("CREATE SCHEMA IF NOT EXISTS opendata"))
    conn.commit()
    insp = inspect(conn)
    tiene_version = insp.has_table("alembic_version", schema="opendata")
    poblado       = insp.has_table("resource", schema="opendata")
print("stamp" if (poblado and not tiene_version) else "ok")
PYEOF
)

# BD preexistente que perdió su registro de versión: marcamos el head conocido
# en vez de re-aplicar desde base (que rompería con DDL no idempotente).
if [ "$NEED_STAMP" = "stamp" ]; then
    echo "[entrypoint] BD preexistente sin alembic_version -> stamp heads (no re-aplico desde base)"
    alembic stamp heads
fi

# Aplica SOLO lo pendiente (el delta). Ya no se borra alembic_version en cada arranque.
alembic upgrade heads

echo "[entrypoint] Seeding fetcher catalog..."
python seed_fetchers.py
python seed_rbac.py
python seed_manifests.py

echo "[entrypoint] Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
