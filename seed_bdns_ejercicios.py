"""Alta de la serie de recursos BDNS por ejercicio + su colección.

Para cada búsqueda BDNS con ventana temporal crea:
  - una COLECCIÓN (recurso padre, genera_colecciones=True) que representa el
    histórico completo y puede correrse con fechas de runtime, y
  - un RECURSO HIJO por EJERCICIO (parent_resource_id → colección), cada uno
    acotado a su año vía fecha_desde/fecha_hasta (el RESTFetcher las inyecta como
    fechaDesde/fechaHasta).

Los ejercicios NO se hardcodean: se detectan sondeando el SNPSAP (años con
registros), de más reciente hacia atrás, hasta el primero con datos. Idempotente:
upsert por nombre. Pensado para correr en ODM (necesita DATABASE_URL).

    python seed_bdns_ejercicios.py                 # todos los endpoints
    python seed_bdns_ejercicios.py concesiones      # solo uno
    python seed_bdns_ejercicios.py --suelo 2022     # fija el suelo (sin sondeo)
"""
from __future__ import annotations

import sys
import json
import datetime as _dt
from typing import List, Optional

import requests

from app.database import SessionLocal
from app.models import Resource, ResourceParam, Fetcher, Publisher

API_BASE = "https://www.infosubvenciones.es/bdnstrans/api"
PUBLISHER_ACRONIMO = "BDNS"
FETCHER_CODES = ("API REST Paginada", "API REST")  # se usa el primero registrado
MIN_YEAR = 2008  # cota inferior del sondeo

# endpoint → (etiqueta, order (clave única para paginación profunda), target_table)
ENDPOINTS = {
    "convocatorias":        ("Convocatorias", "numeroConvocatoria", "bdns_convocatorias"),
    "concesiones":          ("Concesiones",   "codConcesion",       "bdns_concesiones"),
    "minimis":              ("Mínimis",        "numeroConvocatoria", "bdns_minimis"),
    "ayudasestado":         ("Ayudas de Estado", "codConcesion",    "bdns_ayudasestado"),
    "grandesbeneficiarios": ("Grandes Beneficiarios", "beneficiario", "bdns_grandesbeneficiarios"),
    "sanciones":            ("Sanciones",     "fechaConcesion",     "bdns_sanciones"),
    "partidospoliticos":    ("Partidos Políticos", "codConcesion",  "bdns_partidospoliticos"),
    "planesestrategicos":   ("Planes Estratégicos", "vigenciaDesde", "bdns_planesestrategicos"),
}


# ── sondeo de ejercicios con registros ───────────────────────────────────────
def total_anio(session_http: requests.Session, endpoint: str, order: str, anio: int) -> Optional[int]:
    """totalElements de un ejercicio (dd/mm/yyyy, que es lo que el SNPSAP entiende)."""
    q = {"vpd": "GE", "order": order, "direccion": "desc", "pageSize": 1, "page": 1,
         "fechaDesde": f"01/01/{anio}", "fechaHasta": f"31/12/{anio}"}
    for intento in range(2):  # años enormes (p.ej. 2025) pueden tardar; un reintento
        try:
            r = session_http.get(f"{API_BASE}/{endpoint}/busqueda", params=q,
                                 headers={"Accept": "application/json", "User-Agent": "odm-seed"},
                                 timeout=45)
            if r.status_code == 200:
                return r.json().get("totalElements")
        except Exception:
            pass
    return None


def ejercicios_con_registros(endpoint: str, order: str) -> List[int]:
    """Años con registros, de hoy hacia atrás hasta MIN_YEAR. Se detiene tras dos
    ceros consecutivos una vez vistos datos (corta el barrido sin perder huecos
    cortos)."""
    s = requests.Session()
    actual = _dt.date.today().year
    anios, ceros, visto = [], 0, False
    for y in range(actual, MIN_YEAR - 1, -1):
        t = total_anio(s, endpoint, order, y)
        if t and t > 0:
            anios.append(y); visto = True; ceros = 0
        else:
            ceros += 1
            if visto and ceros >= 2:
                break
    return sorted(anios)


# ── upsert de recursos ───────────────────────────────────────────────────────
def _params_base(endpoint: str, order: str) -> dict:
    return {
        "url": f"{API_BASE}/{endpoint}/busqueda",
        "method": "get",
        "pagination": "page_number",
        "page_param": "page",
        "page_size_param": "pageSize",
        "page_size": "10000",
        "start_page": "0",
        "content_field": "content",
        "id_field": "id",
        "query_params": json.dumps({"vpd": "GE", "order": order, "direccion": "desc"}, ensure_ascii=False),
        "timeout": "120",
        "delay_between_pages": "0.3",
        "max_records": "0",
    }


def _upsert_resource(db, *, name, fetcher_id, publisher_id, target_table, schedule,
                     params: dict, parent_id=None, genera_colecciones=False) -> Resource:
    r = db.query(Resource).filter(Resource.name == name, Resource.deleted_at.is_(None)).first()
    if r is None:
        r = Resource(name=name, fetcher_id=fetcher_id, publisher_id=publisher_id,
                     target_table=target_table, active=True, schedule=schedule,
                     parent_resource_id=parent_id, genera_colecciones=genera_colecciones)
        db.add(r); db.flush()
    else:
        r.fetcher_id = fetcher_id; r.publisher_id = publisher_id
        r.target_table = target_table; r.schedule = schedule
        r.parent_resource_id = parent_id; r.genera_colecciones = genera_colecciones
        db.query(ResourceParam).filter(ResourceParam.resource_id == r.id).delete()
        db.flush()
    for k, v in params.items():
        db.add(ResourceParam(resource_id=r.id, key=k, value=str(v)))
    return r


def generar(endpoints: List[str], suelo: Optional[int]):
    db = SessionLocal()
    try:
        fetcher = (db.query(Fetcher)
                   .filter(Fetcher.code.in_(FETCHER_CODES), Fetcher.deleted_at.is_(None))
                   .order_by(Fetcher.code).first())
        if not fetcher:
            raise SystemExit(f"No hay fetcher registrado entre {FETCHER_CODES}.")
        pub = db.query(Publisher).filter(Publisher.acronimo == PUBLISHER_ACRONIMO,
                                         Publisher.deleted_at.is_(None)).first()
        if not pub:
            raise SystemExit(f"No existe el publisher {PUBLISHER_ACRONIMO} (corre seed_resources primero).")

        for ep in endpoints:
            etiqueta, order, tabla = ENDPOINTS[ep]
            anios = [y for y in range(_dt.date.today().year, suelo - 1, -1)] if suelo else \
                ejercicios_con_registros(ep, order)
            if not anios:
                print(f"· {etiqueta}: sin ejercicios con registros — omitido."); continue

            # Colección (padre): histórico completo, corre con fechas de runtime.
            col = _upsert_resource(
                db, name=f"BDNS · {etiqueta} (histórico por ejercicio)",
                fetcher_id=fetcher.id, publisher_id=pub.id, target_table=tabla,
                schedule="0 3 5 * *", params=_params_base(ep, order),
                parent_id=None, genera_colecciones=True)

            # Un hijo por ejercicio (hacia atrás), acotado por su ventana.
            for y in sorted(anios, reverse=True):
                p = _params_base(ep, order)
                p["fecha_desde"] = f"01/01/{y}"
                p["fecha_hasta"] = f"31/12/{y}"
                _upsert_resource(
                    db, name=f"BDNS · {etiqueta} {y}", fetcher_id=fetcher.id,
                    publisher_id=pub.id, target_table=tabla, schedule=None,
                    params=p, parent_id=col.id, genera_colecciones=False)
            print(f"· {etiqueta}: colección + {len(anios)} ejercicios "
                  f"({min(anios)}–{max(anios)}).")
        db.commit()
        print("Hecho.")
    except Exception:
        db.rollback(); raise
    finally:
        db.close()


def main(argv: List[str]):
    suelo = None
    eps = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--suelo":
            suelo = int(argv[i + 1]); i += 2; continue
        if a in ENDPOINTS:
            eps.append(a)
        i += 1
    generar(eps or list(ENDPOINTS.keys()), suelo)


if __name__ == "__main__":
    main(sys.argv[1:])
