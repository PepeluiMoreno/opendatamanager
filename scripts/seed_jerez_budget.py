"""
scripts/seed_jerez_budget.py

Registra en opendatamanager los Resources del módulo financiero
de JerezBudgetAPI usando el fetcher PDF_PAGE.

Uso:
    cd opendatamanager
    python scripts/seed_jerez_budget.py [--dry-run]

Crea (si no existen):
  - Publisher: Ayuntamiento de Jerez de la Frontera
  - Fetcher:   PDF_PAGE  (debe existir ya en BD)
  - Resources:
      · jerez-ejecucion-gastos
      · jerez-ejecucion-ingresos
      · jerez-modificaciones-presupuestarias
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

from app.database import SessionLocal
from app.models import Fetcher, Publisher, Resource, ResourceParam

BASE_URL = "https://transparencia.jerez.es"
URL_TEMPLATE = f"{BASE_URL}/infopublica/economica/presupuesto/{{ejercicio}}"
URL_OVERRIDES = '{"2026": "/infopublica/economica/presupuesto/2026/prorroga-2025"}'

RESOURCES = [
    {
        "name": "jerez-ejecucion-gastos",
        "description": "Ejecución presupuestaria de gastos del Ayuntamiento de Jerez. "
                       "Datos mensuales en XLSX por ejercicio fiscal.",
        "params": {
            "url_template":  URL_TEMPLATE,
            "url_overrides": URL_OVERRIDES,
            "pdf_dir":       "data/pdfs/jerez/presupuesto/{ejercicio}/gastos",
            "link_selector": "a[href$='.xlsx']",
            "script_module": "etl.scripts.execution_expenses",
            "delay_seconds": "1.0",
        },
    },
    {
        "name": "jerez-ejecucion-ingresos",
        "description": "Ejecución presupuestaria de ingresos del Ayuntamiento de Jerez. "
                       "Datos mensuales en XLSX por ejercicio fiscal.",
        "params": {
            "url_template":  URL_TEMPLATE,
            "url_overrides": URL_OVERRIDES,
            "pdf_dir":       "data/pdfs/jerez/presupuesto/{ejercicio}/ingresos",
            "link_selector": "a[href$='.xlsx']",
            "script_module": "etl.scripts.execution_revenues",
            "delay_seconds": "1.0",
        },
    },
    {
        "name": "jerez-modificaciones-presupuestarias",
        "description": "Modificaciones presupuestarias del Ayuntamiento de Jerez. "
                       "Metadatos extraídos de PDFs por ejercicio fiscal.",
        "params": {
            "url_template":  URL_TEMPLATE,
            "url_overrides": URL_OVERRIDES,
            "pdf_dir":       "data/pdfs/jerez/presupuesto/{ejercicio}/modificaciones",
            "link_selector": "a[href$='.pdf']",
            "script_module": "etl.scripts.budget_modifications",
            "delay_seconds": "1.5",
        },
    },
]


def seed(dry_run: bool = False):
    db = SessionLocal()
    try:
        # ── Publisher ─────────────────────────────────────────────────────────
        publisher = db.query(Publisher).filter_by(
            nombre="Ayuntamiento de Jerez de la Frontera"
        ).first()
        if not publisher:
            publisher = Publisher(
                nombre="Ayuntamiento de Jerez de la Frontera",
                acronimo="AJF",
                nivel="LOCAL",
                pais="España",
                comunidad_autonoma="Andalucía",
                provincia="Cádiz",
                municipio="Jerez de la Frontera",
                portal_url="https://transparencia.jerez.es",
            )
            if not dry_run:
                db.add(publisher)
                db.flush()
            print(f"  [+] Publisher: {publisher.nombre}")
        else:
            print(f"  [=] Publisher ya existe: {publisher.nombre}")

        # ── Fetcher PDF_PAGE ──────────────────────────────────────────────────
        fetcher = db.query(Fetcher).filter(
            Fetcher.code == "PDF_PAGE",
            Fetcher.deleted_at == None,
        ).first()
        if not fetcher:
            print("  [!] Fetcher PDF_PAGE no encontrado en BD.")
            print("      Registra primero el fetcher desde la UI o con seed_fetchers.py")
            sys.exit(1)
        print(f"  [=] Fetcher: {fetcher.code} ({fetcher.id})")

        # ── Resources ─────────────────────────────────────────────────────────
        for res_def in RESOURCES:
            existing = db.query(Resource).filter_by(
                name=res_def["name"]
            ).first()
            if existing:
                print(f"  [=] Resource ya existe: {res_def['name']}")
                continue

            resource = Resource(
                name=res_def["name"],
                description=res_def["description"],
                fetcher_id=fetcher.id,
                publisher_id=publisher.id if not dry_run else None,
                active=True,
            )

            if not dry_run:
                db.add(resource)
                db.flush()

                for key, value in res_def["params"].items():
                    db.add(ResourceParam(
                        resource_id=resource.id,
                        key=key,
                        value=value,
                    ))

            print(f"  [+] Resource: {res_def['name']}")
            for k, v in res_def["params"].items():
                print(f"        {k} = {v}")

        if not dry_run:
            db.commit()
            print("\n✅ Seed completado.")
        else:
            print("\n[DRY-RUN] Nada guardado.")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("Seeding JerezBudgetAPI resources en opendatamanager...\n")
    seed(dry_run=args.dry_run)
