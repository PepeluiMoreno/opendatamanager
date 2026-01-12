"""
Script para limpiar tipos de fetcher obsoletos.
Ejecutar con: python -m scripts.cleanup_old_fetchers
"""
from app.database import SessionLocal
from app.models import FetcherType

# Tipos obsoletos a eliminar
OBSOLETE_CODES = ["REST", "RER", "HTML Scraper"]

def cleanup_old_fetchers():
    """Elimina fetcher types obsoletos que ya no se usan"""
    db = SessionLocal()
    try:
        for code in OBSOLETE_CODES:
            fetcher = db.query(FetcherType).filter(
                FetcherType.code == code
            ).first()

            if fetcher:
                db.delete(fetcher)
                print(f"[-] Eliminado FetcherType obsoleto: '{code}'")
            else:
                print(f"[OK] FetcherType '{code}' ya no existe")

        db.commit()
        print("\n[OK] Limpieza completada")

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Error al limpiar fetcher types: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    cleanup_old_fetchers()
