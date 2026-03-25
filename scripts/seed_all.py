"""
Orquestador principal de seeding.

Reconstruye el estado base de la BD ejecutando los seeds en orden de dependencia:
    01. fetchers       — tipos de fetcher (sin FKs)
    02. fetcher_params — parámetros de tipo (FK → fetcher)
    03. resources      — recursos concretos y sus params (FK → fetcher)

Uso:
    # Con la URL del .env (Docker):
    python -m scripts.seed_all

    # Override local (fuera de Docker):
    DATABASE_URL="postgresql+psycopg2://sipi:CHANGE_ME_IN_PRODUCTION@localhost:5433/odmgr" \\
        python -m scripts.seed_all

    # Solo un paso concreto:
    python -m scripts.seeds.fetchers
    python -m scripts.seeds.fetcher_params
    python -m scripts.seeds.resources
"""
import sys
from scripts.seeds._db import get_session
from scripts.seeds import fetchers, fetcher_params, resources


STEPS = [
    ("01 — Fetchers",        fetchers.seed),
    ("02 — Fetcher params",  fetcher_params.seed),
    ("03 — Resources",       resources.seed),
]


def main():
    db = get_session()
    print("=== seed_all: iniciando ===")
    try:
        for label, fn in STEPS:
            print(f"\n[{label}]")
            fn(db)
        print("\n=== seed_all: completado ===")
    except Exception as exc:
        print(f"\nERROR en seeding: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
