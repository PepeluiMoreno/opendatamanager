"""
Crea los resources de la Fiscalía General del Estado en OpenDataManager.

Resources:
  1. Fiscalías - Directorio por Comunidad Autónoma
     Fetcher: HTML SearchLoop (modo url_template)
     Fuente:  https://www.fiscal.es/{comunidad}
     Datos:   Fiscal Superior, Teniente Fiscal, email, teléfono, dirección, provincias

Run dentro del contenedor:
  docker exec odmgr_app python scripts/seed_fiscal.py
"""
import sys
sys.path.insert(0, "/app")

import json
from uuid import uuid4
from app.database import SessionLocal
from app.models import Fetcher, Resource, ResourceParam

db = SessionLocal()

# ── Fetcher HTML SearchLoop ──────────────────────────────────────────────────
sl = db.query(Fetcher).filter(
    Fetcher.class_path == "app.fetchers.searchloop_html.SearchLoopHtmlFetcher"
).first()
if not sl:
    print("ERROR: Fetcher 'HTML SearchLoop' no encontrado en BD.")
    db.close()
    sys.exit(1)
print(f"  Fetcher HTML SearchLoop: {sl.id}")


def make_resource(name, fetcher, params, publisher):
    r = db.query(Resource).filter(Resource.name == name).first()
    if r:
        print(f"  Resource '{name}' ya existe ({r.id})")
        return r
    r = Resource(
        id=uuid4(),
        name=name,
        publisher=publisher,
        fetcher_id=fetcher.id,
        active=True,
    )
    db.add(r)
    db.flush()
    for k, v in params.items():
        db.add(ResourceParam(id=uuid4(), resource_id=r.id, key=k, value=str(v)))
    print(f"✓ Resource '{name}' creado: {r.id}")
    return r


# ── Comunidades autónomas (slugs en fiscal.es) ───────────────────────────────
COMUNIDADES = [
    "andalucia",
    "aragon",
    "asturias",
    "baleares",
    "canarias",
    "cantabria",
    "castilla-la-mancha",
    "castilla-y-leon",
    "cataluna",
    "comunidad-valenciana",
    "extremadura",
    "galicia",
    "la-rioja",
    "madrid",
    "murcia",
    "navarra",
    "pais-vasco",
]

# ── Selectores CSS (estructura .mj-fiscalias consistente en todas las CCAA) ──
FIELD_SELECTORS = json.dumps({
    "fiscal_superior":      ".mj-aside__list li:nth-child(1) p.mb-10",
    "teniente_fiscal":      ".mj-aside__list li:nth-child(2) p.mb-10",
    "ultima_actualizacion": ".mj-fiscalias__update-block p",
})

FIELD_ATTR_SELECTORS = json.dumps({
    "email":    {"selector": ".mj-contactInfo a.mj-link[href^='mailto:']", "attr": "href"},
    "telefono": {"selector": ".mj-contactInfo a[href^='tel:']",            "attr": "href"},
})

# Todos los teléfonos (puede haber varios)
FIELD_ALL_SELECTORS = json.dumps({
    "telefonos":  ".mj-contactInfo a[href^='tel:']",
    "provincias": ".mj-fiscalias__list li.mj-fiscalias__list--item p.mj-box__default--text",
})

# Dirección: busca el span label "Dirección" dentro del bloque de contacto
FIELD_LABEL_SELECTORS = json.dumps({
    "direccion": {"container": ".mj-contactInfo", "label": "Dirección"},
})

make_resource(
    name="Fiscalías - Directorio por Comunidad Autónoma",
    fetcher=sl,
    publisher="Fiscalía General del Estado",
    params={
        # Modo url_template: {value} se sustituye por cada comunidad
        "url_template":           "https://www.fiscal.es/{value}",
        "search_field_name":      "comunidad",
        "search_field_values":    ",".join(COMUNIDADES),
        # Extracción de campos
        "field_selectors":        FIELD_SELECTORS,
        "field_attr_selectors":   FIELD_ATTR_SELECTORS,
        "field_all_selectors":    FIELD_ALL_SELECTORS,
        "field_label_selectors":  FIELD_LABEL_SELECTORS,
        "field_all_separator":    " | ",
        # Cortesía con el servidor
        "delay_between_searches": "1.5",
        "timeout":                "30",
    },
)

db.commit()
db.close()
print("Done.")
