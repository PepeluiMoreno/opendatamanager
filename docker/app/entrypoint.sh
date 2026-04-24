#!/bin/bash
set -e

echo "[entrypoint] Waiting for PostgreSQL..."
until pg_isready -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "${DB_USER:-postgres}" -q; do
    sleep 1
done
echo "[entrypoint] PostgreSQL ready."

echo "[entrypoint] Running migrations..."

# Inspect current alembic state directly in the DB.
# Returns: NO_TABLE (fresh DB), EMPTY (no rows), or the version_num string.
CURRENT_VERSION=$(python - <<'PYEOF'
import os
from sqlalchemy import create_engine, text
engine = create_engine(os.environ["DATABASE_URL"])
try:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).fetchone()
        print(row[0] if row else "EMPTY")
except Exception:
    print("NO_TABLE")
PYEOF
)

echo "[entrypoint] Alembic version in DB: $CURRENT_VERSION"

if [ "$CURRENT_VERSION" = "NO_TABLE" ] || [ "$CURRENT_VERSION" = "EMPTY" ]; then
    # Fresh install — alembic upgrade heads will create the full schema from 0001_initial
    echo "[entrypoint] Fresh DB — alembic upgrade heads will build the schema."

elif [ "$CURRENT_VERSION" != "0001_initial" ]; then
    # Existing DB pointing to a deleted revision (migration consolidation).
    echo "[entrypoint] Stale revision '$CURRENT_VERSION' — re-stamping to 0001_initial..."

    python - <<'PYEOF'
import os
from sqlalchemy import create_engine, text
engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as conn:
    conn.execute(text("UPDATE alembic_version SET version_num = '0001_initial'"))
    conn.commit()
print("[entrypoint] Stamped to 0001_initial.")
PYEOF

    # Apply columns added in this consolidation round (idempotent)
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
