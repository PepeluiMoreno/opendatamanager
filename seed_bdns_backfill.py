"""Backfill BDNS por ejercicio/mes — concurrencia acotada, hacia atrás.

Ejecuta, de MÁS RECIENTE a MÁS ANTIGUO, los recursos hijos de una colección BDNS
creados por `seed_bdns_ejercicios.py` (`BDNS · Concesiones 2026`, `… 2025-12`…).
Usa el camino del SCHEDULER —`FetcherManager.run(session, resource_id)`— que NO
pasa por los guards del refresco on-demand (cooldown, cuota, principal).

Concurrencia ACOTADA (I/O-bound → hilos): un pool de `--workers` ejecuta varias
ventanas a la vez, cada worker con su PROPIA sesión de BD. El tope por defecto es
`max_concurrent_processes` (AppConfig, def. 3) para no saturar el SNPSAP ni pisar
otras ejecuciones programadas. La cortesía por página la pone el fetcher
(`delay_between_pages`). Corre en ODM (DATABASE_URL) como job de fondo.

    python seed_bdns_backfill.py                          # concesiones, 2026→suelo, workers=cap
    python seed_bdns_backfill.py concesiones --workers 4
    python seed_bdns_backfill.py concesiones --hasta 2024  # solo >=2024
    python seed_bdns_backfill.py concesiones --solo 2025   # un ejercicio (todos sus meses)
    python seed_bdns_backfill.py concesiones --secuencial  # workers=1
    python seed_bdns_backfill.py concesiones --dry-run
"""
from __future__ import annotations

import re
import sys
import datetime as _dt
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Tuple

from app.database import SessionLocal
from app.models import Resource

ETIQUETAS = {
    "convocatorias": "Convocatorias", "concesiones": "Concesiones", "minimis": "Mínimis",
    "ayudasestado": "Ayudas de Estado", "grandesbeneficiarios": "Grandes Beneficiarios",
    "sanciones": "Sanciones", "partidospoliticos": "Partidos Políticos",
    "planesestrategicos": "Planes Estratégicos",
}
# sufijo del nombre: "YYYY" (anual) o "YYYY-MM" (mensual)
_RE_SUF = re.compile(r"\b(20\d{2})(?:-(\d{2}))?$")


def _cap_concurrencia(db) -> int:
    try:
        from app.models import AppConfig
        cfg = db.query(AppConfig).filter(AppConfig.key == "max_concurrent_processes").first()
        return int(cfg.value) if cfg and cfg.value else 3
    except Exception:
        return 3


def _hijos(db, etiqueta: str) -> List[Tuple[Tuple[int, int], str, str]]:
    """[((año, mes), id, nombre)] de los hijos de la colección, más reciente primero.
    mes=0 para hijos anuales (ordenan después de cualquier mensual del mismo año)."""
    col = (db.query(Resource)
           .filter(Resource.name == f"BDNS · {etiqueta} (histórico por ejercicio)",
                   Resource.deleted_at.is_(None)).first())
    if not col:
        return []
    out = []
    for r in (db.query(Resource)
              .filter(Resource.parent_resource_id == col.id, Resource.deleted_at.is_(None)).all()):
        m = _RE_SUF.search(r.name or "")
        if not m:
            continue
        anio = int(m.group(1)); mes = int(m.group(2)) if m.group(2) else 0
        out.append(((anio, mes), str(r.id), r.name))
    out.sort(key=lambda t: t[0], reverse=True)  # hacia atrás
    return out


def _ejecutar(resource_id: str, nombre: str) -> str:
    """Tarea de worker: sesión propia + FetcherManager.run. Devuelve línea de log."""
    from app.manager.fetcher_manager import FetcherManager
    db = SessionLocal()
    t0 = _dt.datetime.utcnow()
    try:
        ds = FetcherManager.run(db, resource_id)
        n = getattr(ds, "record_count", None) if ds else None
        secs = int((_dt.datetime.utcnow() - t0).total_seconds())
        return f"  ✓ {nombre}: {n if n is not None else '?'} registros ({secs}s)"
    except Exception as e:  # noqa: BLE001
        return f"  ✗ {nombre}: ERROR {e}"
    finally:
        db.close()


def backfill(endpoint: str, hasta: Optional[int], solo: Optional[int],
             workers: Optional[int], dry_run: bool):
    etiqueta = ETIQUETAS[endpoint]
    db = SessionLocal()
    try:
        objetivos = _hijos(db, etiqueta)
        cap = _cap_concurrencia(db)
    finally:
        db.close()
    if not objetivos:
        raise SystemExit(f"No hay hijos para «{etiqueta}». Corre antes seed_bdns_ejercicios.py {endpoint}.")
    if solo is not None:
        objetivos = [o for o in objetivos if o[0][0] == solo]
    elif hasta is not None:
        objetivos = [o for o in objetivos if o[0][0] >= hasta]
    if not objetivos:
        raise SystemExit("Ninguna ventana coincide con el filtro.")

    w = workers if workers else cap
    w = max(1, min(w, cap, len(objetivos)))  # nunca por encima del tope de ODM
    etiquetas = [n for _, _, n in objetivos]
    print(f"Backfill {etiqueta}: {len(objetivos)} ventanas (hacia atrás), {w} en paralelo"
          + (" [DRY-RUN]" if dry_run else ""))
    if dry_run:
        for _, rid, n in objetivos:
            print(f"  · {n} ({rid})")
        return

    # El pool respeta el orden de envío (más reciente primero); se solapan hasta w.
    with ThreadPoolExecutor(max_workers=w) as ex:
        futs = {ex.submit(_ejecutar, rid, n): n for _, rid, n in objetivos}
        for fut in as_completed(futs):
            print(fut.result(), flush=True)
    print("Backfill terminado.")


def main(argv: List[str]):
    endpoint = "concesiones"; hasta = solo = workers = None; dry = False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--hasta": hasta = int(argv[i + 1]); i += 2; continue
        if a == "--solo": solo = int(argv[i + 1]); i += 2; continue
        if a == "--workers": workers = int(argv[i + 1]); i += 2; continue
        if a == "--secuencial": workers = 1
        elif a == "--dry-run": dry = True
        elif a in ETIQUETAS: endpoint = a
        i += 1
    backfill(endpoint, hasta, solo, workers, dry)


if __name__ == "__main__":
    main(sys.argv[1:])
