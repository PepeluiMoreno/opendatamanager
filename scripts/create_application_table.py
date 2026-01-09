"""
Script para crear la tabla application que falta.
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("Error: DATABASE_URL no configurado")
    exit(1)

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    try:
        # Crear tabla application
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS opendata.application (
                id UUID PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                description TEXT,
                models_path VARCHAR(255) NOT NULL,
                subscribed_projects JSONB NOT NULL,
                active BOOLEAN DEFAULT TRUE
            )
        """))
        conn.commit()
        print("OK - Tabla 'application' creada correctamente")
    except Exception as e:
        print(f"Error: {e}")
