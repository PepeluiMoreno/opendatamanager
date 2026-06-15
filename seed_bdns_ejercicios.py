"""Alta de la serie de recursos BDNS por ejercicio + su colección.

Para cada búsqueda BDNS con ventana temporal crea:
  - una COLECCIÓN (recurso padre, genera_colecciones=True) que representa el
    histórico completo y puede correrse con fechas de runtime, y
  - un RECURSO HIJO por EJERCICIO (parent_resource_id → colección), cada uno
    acotado a su año vía fecha_desde/fecha_hasta (el RESTFetcher las inyecta como
    fechaDesde/fechaHasta).

Los ejercicios NO se hardcodean: se detectan sondeando el SNPSAP (años con
registros), de más reciente hacia atrás, hasta el primero con datos. Los años de
gran volumen (> umbral, def. 2M; p. ej. concesiones 2025 ≈ 19,67M) se trocean en
12 hijos MENSUALES — ventanas someras que paginan más rápido y se paralelizan en
el backfill. Idempotente: upsert por nombre. Pensado para correr en ODM (DATABASE_URL).

    python seed_bdns_ejercicios.py                 # todos los endpoints
    python seed_bdns_ejercicios.py concesiones      # solo uno
    python seed_bdns_ejercicios.py --suelo 2022     # fija el suelo (sin sondeo)
    python seed_bdns_ejercicios.py concesiones --mensual          # fuerza mensual
    python seed_bdns_ejercicios.py concesiones --mensual-umbral 1000000
"""
from __future__ import annotations

import sys
import json
import datetime as _dt
import calendar
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


def ejercicios_con_registros(endpoint: str, order: str):
    """[(año, total)] con registros, de hoy hacia atrás hasta MIN_YEAR. Se detiene
    tras dos ceros consecutivos una vez vistos datos."""
    s = requests.Session()
    actual = _dt.date.today().year
    res, ceros, visto = [], 0, False
    for y in range(actual, MIN_YEAR - 1, -1):
        t = total_anio(s, endpoint, order, y) or 0
        if t > 0:
            res.append((y, t)); visto = True; ceros = 0
        else:
            ceros += 1
            if visto and ceros >= 2:
                break
    return sorted(res)


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


def _hijo_anual(db, fetcher, pub, ep, order, tabla, col, etiqueta, y):
    p = _params_base(ep, order); p["fecha_desde"] = f"01/01/{y}"; p["fecha_hasta"] = f"31/12/{y}"
    _upsert_resource(db, name=f"BDNS · {etiqueta} {y}", fetcher_id=fetcher.id,
                     publisher_id=pub.id, target_table=tabla, schedule=None,
                     params=p, parent_id=col.id, genera_colecciones=False)


def _hijos_mensuales(db, fetcher, pub, ep, order, tabla, col, etiqueta, y):
    """12 hijos (o hasta el mes actual si y es el año en curso). Ventanas someras →
    paginación más rápida y paralelizables."""
    hoy = _dt.date.today()
    ult_mes = hoy.month if y == hoy.year else 12
    n = 0
    for mes in range(1, ult_mes + 1):
        fin = calendar.monthrange(y, mes)[1]
        p = _params_base(ep, order)
        p["fecha_desde"] = f"01/{mes:02d}/{y}"; p["fecha_hasta"] = f"{fin:02d}/{mes:02d}/{y}"
        _upsert_resource(db, name=f"BDNS · {etiqueta} {y}-{mes:02d}", fetcher_id=fetcher.id,
                         publisher_id=pub.id, target_table=tabla, schedule=None,
                         params=p, parent_id=col.id, genera_colecciones=False)
        n += 1
    return n


def generar(endpoints: List[str], suelo: Optional[int], umbral_mensual: int, forzar_mensual: bool, rehacer: bool = False):
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
            col_name = f"BDNS · {etiqueta} (histórico por ejercicio)"

            # Fast-path: si la colección ya tiene hijos, no se re-sondea ni recrea
            # (clave para el entrypoint: arranques baratos tras la primera vez).
            existente = db.query(Resource).filter(
                Resource.name == col_name, Resource.deleted_at.is_(None)).first()
            if existente and not rehacer:
                n_hijos = db.query(Resource).filter(
                    Resource.parent_resource_id == existente.id,
                    Resource.deleted_at.is_(None)).count()
                if n_hijos > 0:
                    print(f"· {etiqueta}: ya existe con {n_hijos} hijos — omitido "
                          f"(--rehacer para regenerar)."); continue

            # (año, total): con --suelo no se sondea (total desconocido → 0).
            pares = [(y, 0) for y in range(_dt.date.today().year, suelo - 1, -1)] if suelo else \
                ejercicios_con_registros(ep, order)
            if not pares:
                print(f"· {etiqueta}: sin ejercicios con registros — omitido."); continue

            col = _upsert_resource(
                db, name=col_name,
                fetcher_id=fetcher.id, publisher_id=pub.id, target_table=tabla,
                schedule=None, params=_params_base(ep, order),
                parent_id=None, genera_colecciones=True)

            anios = [y for y, _ in pares]
            n_anual = n_mensual = 0
            for y, total in sorted(pares, reverse=True):  # hacia atrás
                # Trocea por mes si el volumen del año supera el umbral (o se fuerza).
                # Con --suelo (total=0) solo se trocea si se fuerza explícitamente.
                if forzar_mensual or (total and total > umbral_mensual):
                    n_mensual += _hijos_mensuales(db, fetcher, pub, ep, order, tabla, col, etiqueta, y)
                else:
                    _hijo_anual(db, fetcher, pub, ep, order, tabla, col, etiqueta, y); n_anual += 1
            print(f"· {etiqueta}: colección + {n_anual} anuales + {n_mensual} mensuales "
                  f"({min(anios)}–{max(anios)}).")
        db.commit()
        print("Hecho.")
    except Exception:
        db.rollback(); raise
    finally:
        db.close()


def main(argv: List[str]):
    suelo = None
    umbral_mensual = 2_000_000   # años con más de ~2M de registros → troceo mensual
    forzar_mensual = False
    rehacer = False
    eps = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--suelo":
            suelo = int(argv[i + 1]); i += 2; continue
        if a == "--mensual-umbral":
            umbral_mensual = int(argv[i + 1]); i += 2; continue
        if a == "--mensual":
            forzar_mensual = True
        elif a == "--rehacer":
            rehacer = True
        elif a in ENDPOINTS:
            eps.append(a)
        i += 1
    generar(eps or list(ENDPOINTS.keys()), suelo, umbral_mensual, forzar_mensual, rehacer)


if __name__ == "__main__":
    main(sys.argv[1:])
