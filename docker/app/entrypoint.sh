#!/bin/bash
set -e

echo "[entrypoint] Waiting for PostgreSQL..."
until pg_isready -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "${DB_USER:-postgres}" -q; do
    sleep 1
done
echo "[entrypoint] PostgreSQL ready."

echo "[entrypoint] Running migrations..."

# alembic_version is in schema 'opendata' (version_table_schema in alembic.ini).
# Determine the DB state before letting alembic run, so we can fix stale revisions.
DB_STATE=$(python - <<'PYEOF'
import os
from sqlalchemy import create_engine, text
engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as conn:
    # Ensure opendata schema exists before querying
    conn.execute(text("CREATE SCHEMA IF NOT EXISTS opendata"))
    conn.commit()
    try:
        row = conn.execute(text(
            "SELECT version_num FROM opendata.alembic_version LIMIT 1"
        )).fetchone()
        version = row[0] if row else None
    except Exception:
        version = None
        # alembic_version missing — check if opendata tables exist
        try:
            conn.execute(text("SELECT 1 FROM opendata.resource LIMIT 1"))
            print("NEEDS_STAMP")
        except Exception:
            print("FRESH")
        import sys; sys.exit(0)

    if version == "0001_initial":
        print("OK")
    elif version is None:
        print("NEEDS_STAMP")
    else:
        print(version)
PYEOF
)

echo "[entrypoint] DB state: $DB_STATE"

case "$DB_STATE" in
  FRESH)
    echo "[entrypoint] Fresh DB — alembic upgrade heads will build the full schema."
    ;;
  OK)
    echo "[entrypoint] Already at 0001_initial — no migration needed."
    ;;
  NEEDS_STAMP)
    echo "[entrypoint] Tables exist but no alembic tracking — stamping..."
    python - <<'PYEOF'
import os
from sqlalchemy import create_engine, text
engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS opendata.alembic_version (
            version_num VARCHAR(32) NOT NULL,
            CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
        )
    """))
    conn.execute(text("DELETE FROM opendata.alembic_version"))
    conn.execute(text("INSERT INTO opendata.alembic_version (version_num) VALUES ('0001_initial')"))
    conn.execute(text("""
        ALTER TABLE opendata.resource
            ADD COLUMN IF NOT EXISTS parent_resource_id UUID
                REFERENCES opendata.resource(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS auto_generated BOOLEAN NOT NULL DEFAULT false
    """))
    conn.commit()
print("[entrypoint] Stamped + schema columns ensured.")
PYEOF
    ;;
  *)
    echo "[entrypoint] Stale revision '$DB_STATE' — re-stamping to 0001_initial..."
    python - <<'PYEOF'
import os
from sqlalchemy import create_engine, text
engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as conn:
    conn.execute(text("UPDATE opendata.alembic_version SET version_num = '0001_initial'"))
    conn.execute(text("""
        ALTER TABLE opendata.resource
            ADD COLUMN IF NOT EXISTS parent_resource_id UUID
                REFERENCES opendata.resource(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS auto_generated BOOLEAN NOT NULL DEFAULT false
    """))
    conn.commit()
print("[entrypoint] Stamped + schema columns ensured.")
PYEOF
    ;;
esac

alembic upgrade heads

echo "[entrypoint] Seeding fetcher catalog..."
python seed_fetchers.py || echo "[entrypoint] WARNING: seed_fetchers.py failed — app arranca igualmente."

echo "[entrypoint] Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
