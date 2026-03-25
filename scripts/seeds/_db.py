"""
DB connection helper for seed scripts.

Priority:
  1. DATABASE_URL env var (already exported)
  2. .env file in project root
  3. Fallback: localhost:5433 dev credentials

Usage from any seed script:
    from scripts.seeds._db import get_session
    db = get_session()
"""
import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

_DEV_FALLBACK = (
    "postgresql+psycopg2://sipi:CHANGE_ME_IN_PRODUCTION@localhost:5433/odmgr"
)


def get_engine():
    url = os.environ.get("DATABASE_URL")
    if not url:
        env_path = Path(__file__).resolve().parents[2] / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line.startswith("DATABASE_URL=") and not line.startswith("#"):
                    url = line.split("=", 1)[1].strip()
                    break
    if not url:
        url = _DEV_FALLBACK
    return create_engine(url)


def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()
