"""
Orquestador principal de seeding.

Ejecuta en orden:
  1. seed_fetchers  — catálogo de tipos de fetcher (API admin GraphQL)
  2. seed_resources — publishers y resources fundacionales (API admin GraphQL)

Ambos scripts son idempotentes (upsert por nombre/acrónimo).

Uso:
    python scripts/seed_all.py
    # o desde el contenedor:
    docker exec odmgr_app python scripts/seed_all.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seed_fetchers import seed as seed_fetchers
from seed_resources import seed as seed_resources


STEPS = [
    ("01 — Fetchers base",                seed_fetchers),
    ("02 — Publishers y Resources base",  seed_resources),
]


def main():
    print("=== seed_all: iniciando ===")
    try:
        for label, fn in STEPS:
            print(f"\n[{label}]")
            fn()
        print("\n=== seed_all: completado ===")
    except Exception as exc:
        print(f"\nERROR en seeding: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
