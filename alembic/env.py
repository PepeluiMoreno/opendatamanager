# alembic/env.py
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

# =========================
# Cargar variables de entorno
# =========================
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# =========================
# Configuración Alembic
# =========================
config = context.config
config_file = config.config_file_name or os.path.join(os.path.dirname(__file__), "alembic.ini")
fileConfig(config_file)

# =========================
# Importar modelos
# =========================
from app.database import Base  # Base con metadata.schema='opendata'
from app.models import *       # Todos los modelos

target_metadata = Base.metadata

# =========================
# Offline migrations
# =========================
def run_migrations_offline():
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema="opendata",  # tabla alembic_version en opendata
        include_schemas=True,              # usar metadata.schema
    )
    with context.begin_transaction():
        context.run_migrations()

# =========================
# Online migrations
# =========================
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
            include_schemas=True,
        )
        with context.begin_transaction():
            context.run_migrations()

# =========================
# Ejecutar según modo
# =========================
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

