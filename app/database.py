import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Solo crear engine si DATABASE_URL está disponible (evita errores en import time)
engine = None
SessionLocal = None

if DATABASE_URL:
    # Pool dimensionado para la concurrencia real: cada run retiene UNA conexión
    # durante todo el crawl (~minutos) y el SSE de logs abre sesiones cortas cada
    # segundo por panel abierto. Con el pool por defecto (5+10) varios discovery a
    # la vez + paneles abiertos lo agotaban y, al ser 1 worker uvicorn, una espera
    # de conexión bloqueaba el event loop → el frontend daba el backend por caído.
    # pool_pre_ping descarta conexiones muertas tras un redeploy/idle; pool_recycle
    # las renueva antes del corte de inactividad de Postgres.
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_size=20,
        max_overflow=40,
        pool_timeout=30,
        pool_pre_ping=True,
        pool_recycle=1800,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    if SessionLocal is None:
        raise RuntimeError("Database not configured. Check DATABASE_URL environment variable.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
