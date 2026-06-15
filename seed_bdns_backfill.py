"""Backfill BDNS por ejercicio — encola hacia atrás los hijos de la colección.

Ejecuta, de MÁS RECIENTE a MÁS ANTIGUO, los recursos hijos por ejercicio creados
por `seed_bdns_ejercicios.py` (p. ej. `BDNS · Concesiones 2026` … `2022`). Usa el
camino del SCHEDULER —`FetcherManager.run(session, resource_id)`— que NO pasa por
los guards del refresco on-demand (cooldown, cuota diaria, principal autenticado):
es un backfill de operador.

Síncrono y secuencial: procesa un ejercicio entero antes del siguiente (un año
grande como 2025 ≈ 19,67M puede tardar). Pensado para correr en ODM como job de
fondo (DATABASE_URL).

    python seed_bdns_backfill.py                     # concesiones, todos los años (hoy→suelo)
    python seed_bdns_backfill.py convocatorias        # otra búsqueda
    python seed_bdns_backfill.py concesiones --hasta 2024   # solo 2026,2025,2024
    python seed_bdns_backfill.py concesiones --solo 2023    # un único ejercicio
    python seed_bdns_backfill.py concesiones --dry-run      # solo lista, no ejecuta
"""
from __future__ import annotations

import re
import sys
import datetime as _dt
from typing import List, Optional

from app.database import SessionLocal
from app.models import Resource

# etiqueta de colección por endpoint (debe casar con seed_bdns_ejercicios.py)
ETIQUETAS = {
    "convocatorias": "Convocatorias", "concesiones": "Concesiones", "minimis": "Mínimis",
    "ayudasestado": "Ayudas de Estado", "grandesbeneficiarios": "Grandes Beneficiarios",
    "sanciones": "Sanciones", "partidospoliticos": "Partidos Políticos",
    "planesestrategicos": "Planes Estratégicos",
}
_RE_ANIO = re.compile(r"\b(20\d{2})$")


def _hijos_por_ejercicio(db, etiqueta: str):
    """(año, recurso) de los hijos de la colección, ordenados de más reciente a más antiguo."""
    col = (db.query(Resource)
           .filter(Resource.name == f"BDNS · {etiqueta} (histórico por ejercicio)",
                   Resource.deleted_at.is_(None))
           .first())
    if not col:
        return []
    hijos = (db.query(Resource)
             .filter(Resource.parent_resource_id == col.id, Resource.deleted_at.is_(None))
             .all())
    out = []
    for r in hijos:
        m = _RE_ANIO.search(r.name or "")
        if m:
            out.append((int(m.group(1)), r))
    out.sort(key=lambda t: t[0], reverse=True)  # hacia atrás
    return out


def backfill(endpoint: str, hasta: Optional[int], solo: Optional[int], dry_run: bool):
    from app.manager.fetcher_manager import FetcherManager
    etiqueta = ETIQUETAS[endpoint]
    db = SessionLocal()
    try:
        objetivos = _hijos_por_ejercicio(db, etiqueta)
        if not objetivos:
            raise SystemExit(f"No hay hijos por ejercicio para «{etiqueta}». "
                             f"Corre antes seed_bdns_ejercicios.py {endpoint}.")
        if solo is not None:
            objetivos = [(y, r) for y, r in objetivos if y == solo]
        elif hasta is not None:
            objetivos = [(y, r) for y, r in objetivos if y >= hasta]
        if not objetivos:
            raise SystemExit("Ningún ejercicio coincide con el filtro.")

        print(f"Backfill {etiqueta} (hacia atrás): " + ", ".join(str(y) for y, _ in objetivos)
              + (" [DRY-RUN]" if dry_run else ""))
        for y, r in objetivos:
            if dry_run:
                print(f"  · {y}: {r.name} ({r.id}) — no ejecutado (dry-run)")
                continue
            t0 = _dt.datetime.utcnow()
            print(f"  · {y}: ejecutando {r.name} …", flush=True)
            try:
                ds = FetcherManager.run(db, str(r.id))
                n = getattr(ds, "record_count", None) if ds else None
                secs = int((_dt.datetime.utcnow() - t0).total_seconds())
                print(f"    ✓ {y}: dataset {'?' if ds is None else ds.id} "
                      f"({n if n is not None else '?'} registros, {secs}s)")
            except Exception as e:  # noqa: BLE001
                print(f"    ✗ {y}: ERROR {e}")
                # se continúa con el resto de ejercicios
        print("Backfill terminado.")
    finally:
        db.close()


def main(argv: List[str]):
    endpoint = "concesiones"
    hasta = solo = None
    dry = False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--hasta":
            hasta = int(argv[i + 1]); i += 2; continue
        if a == "--solo":
            solo = int(argv[i + 1]); i += 2; continue
        if a == "--dry-run":
            dry = True
        elif a in ETIQUETAS:
            endpoint = a
        i += 1
    backfill(endpoint, hasta, solo, dry)


if __name__ == "__main__":
    main(sys.argv[1:])
