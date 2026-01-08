# alembic/env.py
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.database import Base  # tu Base con schema='opendata'
from app.models import *  # para que Alembic vea los modelos

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv()

# Leer URL desde .env
DATABASE_URL = os.getenv("DATABASE_URL")

config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata


# =========================
# FILTRO: solo inspeccionar schema 'opendata'
# =========================
def include_name(name, type_, parent_names):
    if type_ == "schema":
        return name == "opendata"
    return True


def run_migrations_offline():
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema="opendata",
        include_name=include_name,  # ← filtro clave
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        {"sqlalchemy.url": DATABASE_URL},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema="opendata",
            include_name=include_name,  # ← filtro clave
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()