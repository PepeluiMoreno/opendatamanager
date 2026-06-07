"""
Retira los 3 Resources legados de Jerez (trío PDF_TABLE viejo) que ya se han
quitado del seed (`seed_resources.py`), pero que siguen vivos en prod ejecutándose
en su cron y dando 404 (el portal cambió las rutas {year}; ver docs/BACKLOG.md e
INFORME_arnes_2026-06-07.md). Los sustituye el Web Tree crawler.

Hace una cosa: soft-delete (`deleted_at = now()`) del Resource y de sus
ejecuciones, igual que la mutation `delete_resource(hard_delete=False)`. Conserva
el historial en BD; solo deja de programarse/ejecutarse.

Uso (en el contenedor app):
    docker exec -it odmgr_app python -u scripts/retire_jerez_legacy.py           # dry-run
    docker exec -it odmgr_app python -u scripts/retire_jerez_legacy.py --apply    # ejecuta

Idempotente: si ya están soft-deleted o no existen, no hace nada.

Nota: esto NO borra las tablas físicas jerez_pmp_mensual / jerez_morosidad_trimestral
/ jerez_deuda_financiera. Solo hace falta un DROP aparte si llegaron a cargarse
datos y quieres tirarlos (opcional). Si quieres borrado físico del Resource y sus
datasets, usa la mutation delete_resource(hard_delete=True) desde el admin.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.database import SessionLocal
from app.models import Resource, ResourceExecution

LEGACY_RESOURCE_NAMES = (
    "Jerez - PMP Mensual (Ley 15/2010)",
    "Jerez - Morosidad Trimestral (Ley 15/2010)",
    "Jerez - Deuda Financiera Anual",
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Retira (soft-delete) el trío PDF_TABLE legado de Jerez.")
    ap.add_argument("--apply", action="store_true", help="Ejecuta los cambios (sin esto, dry-run).")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        resources = db.query(Resource).filter(
            Resource.name.in_(LEGACY_RESOURCE_NAMES),
            Resource.deleted_at.is_(None),
        ).all()

        if not resources:
            print("[retire-jerez] Nada que hacer: no hay recursos legados vivos con esos nombres.")
            return 0

        now = datetime.utcnow()
        print(f"[retire-jerez] {len(resources)} recurso(s) legado(s) vivo(s):")
        for r in resources:
            n_exec = db.query(ResourceExecution).filter(
                ResourceExecution.resource_id == r.id,
                ResourceExecution.deleted_at.is_(None),
            ).count()
            print(f"  · {r.name}  (id={r.id}, target_table={r.target_table}, ejecuciones vivas={n_exec})")
            if args.apply:
                db.query(ResourceExecution).filter(
                    ResourceExecution.resource_id == r.id,
                    ResourceExecution.deleted_at.is_(None),
                ).update({"deleted_at": now}, synchronize_session=False)
                r.deleted_at = now

        if args.apply:
            db.commit()
            print(f"[retire-jerez] HECHO: {len(resources)} recurso(s) soft-deleted (deleted_at={now.isoformat()}).")
        else:
            print("[retire-jerez] DRY-RUN: nada modificado. Relanza con --apply para aplicar.")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
