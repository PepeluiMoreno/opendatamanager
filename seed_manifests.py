"""Importa todos los manifiestos de un directorio en cada arranque (idempotente).

Directorio: MANIFESTS_DIR (default: <repo>/manifests). Cada *.json se importa con
detección a tres bandas (ver app.services.manifests). NO-FATAL: un manifiesto
inválido o un error se registran y NO tumban el arranque. Imprime un resumen y
destaca los conflictos (que requieren intervención humana).
"""
import glob
import json
import os
import sys

from app.database import SessionLocal
from app.services.manifests import import_manifest

MANIFESTS_DIR = os.environ.get(
    "MANIFESTS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "manifests")
)


def main() -> int:
    if SessionLocal is None:
        print("[seed_manifests] DATABASE_URL no configurada; omitiendo.")
        return 0
    ficheros = sorted(glob.glob(os.path.join(MANIFESTS_DIR, "*.json")))
    if not ficheros:
        print(f"[seed_manifests] sin manifiestos en {MANIFESTS_DIR}")
        return 0

    creados = actualizados = 0
    db_ahead, conflictos, errores = [], [], []
    for f in ficheros:
        nombre = os.path.basename(f)
        db = SessionLocal()
        try:
            manifest = json.load(open(f, encoding="utf-8"))
            res = import_manifest(db, manifest, source=nombre)
            if not res.get("ok"):
                print(f"[seed_manifests] {nombre}: INVÁLIDO {res.get('errors')}")
                errores.append(nombre)
                continue
            creados += res["created"]
            actualizados += res["updated"]
            db_ahead += res.get("db_ahead", [])
            conflictos += [f"{nombre}:{c}" for c in res.get("conflicts", [])]
            print(f"[seed_manifests] {nombre}: +{res['created']} ~{res['updated']} "
                  f"saltados={len(res.get('skipped', []))} conflictos={len(res.get('conflicts', []))}")
        except Exception as e:  # noqa: BLE001 — no-fatal por diseño
            print(f"[seed_manifests] {nombre}: ERROR {e}")
            errores.append(nombre)
        finally:
            db.close()

    print(f"[seed_manifests] TOTAL creados={creados} actualizados={actualizados} "
          f"db_ahead={len(db_ahead)} conflictos={len(conflictos)} errores={len(errores)}")
    if conflictos:
        print(f"[seed_manifests] CONFLICTOS (revisar; NO se han pisado): {conflictos}")
    if db_ahead:
        print(f"[seed_manifests] BD por delante del fichero (no tocados): {db_ahead}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
