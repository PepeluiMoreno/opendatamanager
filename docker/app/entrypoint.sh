#!/bin/bash
set -e

echo "[entrypoint] Waiting for PostgreSQL..."
until pg_isready -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "${DB_USER:-postgres}" -q; do
    sleep 1
done
echo "[entrypoint] PostgreSQL ready."

echo "[entrypoint] Running migrations..."

# When migration history is consolidated (many → single 0001_initial), an existing
# production DB may point to a now-deleted revision. Detect and re-stamp gracefully.
ALEMBIC_CURRENT=$(alembic current 2>&1 || true)
if echo "$ALEMBIC_CURRENT" | grep -qi "can't locate"; then
    echo "[entrypoint] Stale alembic revision detected — re-stamping to 0001_initial..."
    python - <<'PYEOF'
import os
from sqlalchemy import create_engine, text
engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as conn:
    conn.execute(text("UPDATE alembic_version SET version_num = '0001_initial'"))
    conn.commit()
print("[entrypoint] Stamped to 0001_initial.")
PYEOF

    # Apply columns added during this consolidation round (idempotent — safe to re-run)
    python - <<'PYEOF'
import os
from sqlalchemy import create_engine, text
engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as conn:
    conn.execute(text("""
        ALTER TABLE opendata.resource
            ADD COLUMN IF NOT EXISTS parent_resource_id UUID
                REFERENCES opendata.resource(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS auto_generated BOOLEAN NOT NULL DEFAULT false
    """))
    conn.commit()
print("[entrypoint] Schema columns ensured (parent_resource_id, auto_generated).")
PYEOF
fi

alembic upgrade heads

echo "[entrypoint] Seeding fetcher catalog..."
python seed_fetchers.py || echo "[entrypoint] WARNING: seed_fetchers.py failed — app arranca igualmente."

echo "[entrypoint] Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
