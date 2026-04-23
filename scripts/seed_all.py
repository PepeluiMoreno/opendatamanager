"""
Orquestador principal de seeding.

Reconstruye un estado de ejemplo de la BD.

No es el camino de despliegue base. En despliegue solo debe ejecutarse
`seed_fetchers.py`, que registra el catálogo inicial de fetchers vía API de
administración. El resto de seeds representan datos de casos de uso.

Uso:
    # Con la URL del .env (Docker/local):
    python -m scripts.seed_all

    # Solo catálogo base de fetchers:
    python seed_fetchers.py
"""
import sys
from seed_fetchers import seed as seed_fetchers
from scripts.seeds._db import get_session
from scripts.seeds import resources


STEPS = [
    ("01 — Fetchers base (API admin)", seed_fetchers),
    ("02 — Resources de ejemplo", resources.seed),
]


def main():
    print("=== seed_all: iniciando ===")
    try:
        for label, fn in STEPS:
            print(f"\n[{label}]")
            if fn is seed_fetchers:
                fn()
            else:
                db = get_session()
                try:
                    fn(db)
                finally:
                    db.close()
        print("\n=== seed_all: completado ===")
    except Exception as exc:
        print(f"\nERROR en seeding: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
