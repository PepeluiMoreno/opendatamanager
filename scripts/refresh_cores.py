# scripts/refresh_cores.py
"""
/scripts/refresh_cores.py
Ejecuta todos los resolvers activos
"""
from app.database import SessionLocal
from app.manager.fetcher_manager import FetcherManager

def main():
    with SessionLocal() as session:
        FetcherManager.run_all(session)

if __name__ == "__main__":
    main()