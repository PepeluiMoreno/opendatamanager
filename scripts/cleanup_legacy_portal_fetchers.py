"""
Limpia los fetchers obsoletos `Portal Documental` y `Portal Files Cataloguer`
tras el rename a `Web Tree`.

Hace tres cosas:

1. Lista Resources que apuntan a los dos fetchers viejos.
2. Para cada Resource, lo migra al fetcher `Web Tree`:
   - Cambia `fetcher_id` al de Web Tree.
   - Conserva el primer valor encontrado entre `start_url` / `url` / `root_url`
     como ResourceParam `root_url` (único param visible del nuevo fetcher).
   - Borra el resto de ResourceParams (eran params específicos de los fetchers
     viejos: max_depth, allowed_extensions, selectores, etc., todos defaults
     internos en WebTreeFetcher).
3. Soft-delete (`deleted_at = now()`) de los dos fetchers obsoletos.

Uso (en el contenedor app):
    docker exec -it odmgr_app python scripts/cleanup_legacy_portal_fetchers.py            # dry-run
    docker exec -it odmgr_app python scripts/cleanup_legacy_portal_fetchers.py --apply    # ejecuta cambios

Idempotente: si los fetchers ya están soft-deleted o no existen, no hace nada.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.database import SessionLocal
from app.models import Fetcher, Resource, ResourceParam


LEGACY_FETCHER_NAMES = ("Portal Documental", "Portal Files Cataloguer")
TARGET_FETCHER_NAME = "Web Tree"
ROOT_URL_SOURCE_KEYS = ("root_url", "start_url", "url")


def _resolve_root_url(params: list[ResourceParam]) -> str | None:
    by_key = {p.key: p.value for p in params}
    for k in ROOT_URL_SOURCE_KEYS:
        if by_key.get(k):
            return by_key[k]
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Limpieza de fetchers Portal Documental / Portal Files Cataloguer")
    parser.add_argument("--apply", action="store_true", help="Ejecuta los cambios. Sin este flag, dry-run.")
    args = parser.parse_args()

    session = SessionLocal()
    try:
        target = (
            session.query(Fetcher)
            .filter(Fetcher.code == TARGET_FETCHER_NAME, Fetcher.deleted_at.is_(None))
            .first()
        )
        if not target:
            print(f"ERROR: Fetcher destino '{TARGET_FETCHER_NAME}' no encontrado en BD. Ejecuta primero seed_fetchers.py.")
            return 2

        legacy = (
            session.query(Fetcher)
            .filter(Fetcher.code.in_(LEGACY_FETCHER_NAMES), Fetcher.deleted_at.is_(None))
            .all()
        )
        if not legacy:
            print("Nada que limpiar: no hay fetchers legacy activos.")
            return 0

        legacy_ids = [f.id for f in legacy]
        affected = (
            session.query(Resource)
            .filter(Resource.fetcher_id.in_(legacy_ids), Resource.deleted_at.is_(None))
            .all()
        )

        print(f"Fetchers legacy a soft-deletear: {[f.code for f in legacy]}")
        print(f"Resources afectados: {len(affected)}")
        for r in affected:
            params_list = list(r.params or [])
            root_url = _resolve_root_url(params_list)
            other_keys = sorted({p.key for p in params_list if p.key not in ROOT_URL_SOURCE_KEYS})
            status = "OK" if root_url else "SIN_URL"
            print(f"  - {r.name} [{status}] root_url={root_url!r} drop_params={other_keys}")

        if not args.apply:
            print("\nDry-run. Re-ejecuta con --apply para confirmar.")
            return 0

        # Apply
        now = datetime.utcnow()
        migrated, skipped = 0, 0
        for r in affected:
            params_list = list(r.params or [])
            root_url = _resolve_root_url(params_list)
            if not root_url:
                print(f"  SKIP {r.name}: sin start_url/url/root_url; revisa manualmente.")
                skipped += 1
                continue

            # Borra todos los ResourceParam y crea solo root_url
            for p in params_list:
                session.delete(p)
            session.add(ResourceParam(resource_id=r.id, key="root_url", value=root_url))
            r.fetcher_id = target.id
            migrated += 1

        for f in legacy:
            f.deleted_at = now

        session.commit()
        print(f"\nMigrados: {migrated} | Saltados: {skipped} | Fetchers soft-deleted: {len(legacy)}")
        return 0

    except Exception as exc:
        session.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
