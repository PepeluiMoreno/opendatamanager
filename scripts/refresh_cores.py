"""
Script para refrescar datos de todas las fuentes activas.
Ejecuta todos los Resources activos y actualiza las tablas correspondientes.

Uso:
    python scripts/refresh_cores.py
"""
from app.database import SessionLocal
from app.manager.fetcher_manager import FetcherManager


def main():
    """Ejecuta todos los resources activos"""
    if SessionLocal is None:
        print("❌ Error: DATABASE_URL no configurado en .env")
        return

    with SessionLocal() as session:
        FetcherManager.run_all(session)


if __name__ == "__main__":
    main()
