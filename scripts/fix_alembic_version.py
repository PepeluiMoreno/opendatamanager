"""
Script temporal para corregir la versión de alembic en la BD.
Elimina la referencia a la migración borrada y establece la versión correcta.
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ Error: DATABASE_URL no configurado en .env")
    exit(1)

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Ver versión actual
    result = conn.execute(text("SELECT version_num FROM opendata.alembic_version"))
    current = result.fetchone()
    print(f"Version actual en BD: {current[0] if current else 'ninguna'}")

    # Actualizar a la versión base correcta
    conn.execute(text("DELETE FROM opendata.alembic_version"))
    conn.execute(text("INSERT INTO opendata.alembic_version (version_num) VALUES ('65c4949bf4df')"))
    conn.commit()

    print("OK - Version actualizada a: 65c4949bf4df (initial opendata schema)")
    print("Ahora puedes ejecutar: python -m alembic upgrade head")
