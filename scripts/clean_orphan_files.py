"""
Detecta y elimina archivos huérfanos en data/ que no tienen referencia en BD.

Tres categorías:
  - data/datasets/{resource_id}/{dataset_id}/  → huérfano si dataset_id no está en BD
  - data/staging/{resource_id}/{execution_id}.jsonl → huérfano si execution_id no está en BD
  - data/logs/{execution_id}.log              → huérfano si execution_id no está en BD

Uso (en el contenedor app):
    docker exec -it odmgr_app python scripts/clean_orphan_files.py
    docker exec -it odmgr_app python scripts/clean_orphan_files.py --delete
"""
import argparse
import os
import shutil
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.database import SessionLocal
from app.models import Dataset, ResourceExecution


def _human(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _dir_size(path: str) -> int:
    total = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, f))
            except OSError:
                pass
    return total


def collect_orphans(db) -> dict:
    from app.models import Resource
    known_resource_ids = {str(r[0]) for r in db.query(Resource.id).all()}
    known_dataset_ids = {str(r[0]) for r in db.query(Dataset.id).all()}
    known_execution_ids = {str(r[0]) for r in db.query(ResourceExecution.id).all()}

    orphans = {"datasets": [], "staging": [], "logs": []}

    # ── data/datasets/{resource_id}/{dataset_id}/ ───────────────────────────
    datasets_root = os.path.join(BASE_DIR, "data", "datasets")
    if os.path.isdir(datasets_root):
        for resource_dir in os.scandir(datasets_root):
            if not resource_dir.is_dir():
                continue
            for ds_dir in os.scandir(resource_dir.path):
                if not ds_dir.is_dir():
                    continue
                ds_id = ds_dir.name
                if ds_id not in known_dataset_ids:
                    size = _dir_size(ds_dir.path)
                    orphans["datasets"].append((ds_dir.path, size))

    # ── data/staging/{resource_id}/ ────────────────────────────────────────
    # Directorio entero huérfano si el resource ya no existe
    # Ficheros individuales huérfanos si la execution ya no existe
    staging_root = os.path.join(BASE_DIR, "data", "staging")
    if os.path.isdir(staging_root):
        for resource_dir in os.scandir(staging_root):
            if not resource_dir.is_dir():
                continue
            if resource_dir.name not in known_resource_ids:
                size = _dir_size(resource_dir.path)
                orphans["staging"].append((resource_dir.path, size))
                continue
            for entry in os.scandir(resource_dir.path):
                if entry.is_file() and entry.name.endswith(".jsonl"):
                    exec_id = entry.name[:-6]  # strip .jsonl
                    if exec_id not in known_execution_ids:
                        size = entry.stat().st_size
                        orphans["staging"].append((entry.path, size))

    # ── data/logs/{execution_id}.log ────────────────────────────────────────
    logs_root = os.path.join(BASE_DIR, "data", "logs")
    if os.path.isdir(logs_root):
        for entry in os.scandir(logs_root):
            if entry.is_file() and entry.name.endswith(".log"):
                exec_id = entry.name[:-4]  # strip .log
                if exec_id not in known_execution_ids:
                    size = entry.stat().st_size
                    orphans["logs"].append((entry.path, size))

    return orphans


def main():
    parser = argparse.ArgumentParser(description="Limpia archivos huérfanos de ejecuciones anteriores.")
    parser.add_argument("--delete", action="store_true", help="Borrar los huérfanos (por defecto: dry-run)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        orphans = collect_orphans(db)
    finally:
        db.close()

    total_files = sum(len(v) for v in orphans.values())
    total_size = sum(s for items in orphans.values() for _, s in items)

    if total_files == 0:
        print("No hay archivos huérfanos. El directorio data/ está limpio.")
        return

    mode = "BORRAR" if args.delete else "DRY-RUN"
    print(f"\n{'='*60}")
    print(f"  Archivos huérfanos encontrados [{mode}]")
    print(f"{'='*60}")

    labels = {
        "datasets": "Datasets sin registro en BD",
        "staging":  "Staging de ejecuciones eliminadas",
        "logs":     "Logs de ejecuciones eliminadas",
    }

    for category, items in orphans.items():
        if not items:
            continue
        cat_size = sum(s for _, s in items)
        print(f"\n[{labels[category]}] — {len(items)} items, {_human(cat_size)}")
        for path, size in sorted(items):
            print(f"  {_human(size):>10}  {path}")

    print(f"\n{'─'*60}")
    print(f"  Total: {total_files} items, {_human(total_size)}")
    print(f"{'─'*60}")

    if not args.delete:
        print("\nEjecuta con --delete para borrar los huérfanos.")
        return

    print("\nBorrando...")
    deleted = 0
    errors = 0
    for category, items in orphans.items():
        for path, _ in items:
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                deleted += 1
            except OSError as e:
                print(f"  ERROR al borrar {path}: {e}")
                errors += 1

    # Limpiar directorios de staging que hayan quedado vacíos tras borrar ficheros sueltos
    staging_root = os.path.join(BASE_DIR, "data", "staging")
    if os.path.isdir(staging_root):
        for resource_dir in os.scandir(staging_root):
            if resource_dir.is_dir() and not any(os.scandir(resource_dir.path)):
                try:
                    os.rmdir(resource_dir.path)
                except OSError:
                    pass

    print(f"\nEliminados {deleted} items ({_human(total_size)}).", end="")
    if errors:
        print(f" {errors} errores.")
    else:
        print()


if __name__ == "__main__":
    main()
