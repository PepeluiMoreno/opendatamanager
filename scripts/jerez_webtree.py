"""Crea los recursos de Jerez económica vía Web Tree — versión censo+extracción.

Decisión §8 (2026-06): la mayoría de los ficheros municipales no son tablas,
así que ya NO se promueve un hijo por propuesta. El script crea:
  1. UN recurso 'Directorio documental' en variante Censo con TODAS las hojas
     del árbol (una fila por fichero: dimensiones+url+formato; sin descargar).
     Es el censo completo y el insumo del CKAN (§9).
  2. Hijos en variante 'Extracción de datos' SOLO para las series/bundles que
     la auditoría (docs/AUDITORIA_jerez_hijos.md) clasificó TABLA_REAL.


Ciclo completo end-to-end (el que en producción harían el crawler + Discovering.vue):
  1. Asegura el publisher de Jerez y un Resource crawler padre 'Web Tree' acotado
     a la sección económica (a07-economica).
  2. discover() recorre el árbol y GroupingInferer.infer() propone agrupaciones
     (series limpias + bundles por carpeta).
  3. Persiste cada propuesta como ResourceCandidate (status discovered).
  4. Promueve cada candidata a un Resource hijo (auto_generated), enlazando
     promoted_resource_id — exactamente lo que hace la mutation promote_candidate.

Idempotente: por defecto, re-descubrir REEMPLAZA el descubrimiento anterior
(retira con soft-delete los hijos auto-generados y candidatos previos del
crawler). Con --append se acumula sin retirar.

Uso:  python scripts/jerez_webtree.py [--max-depth 2] [--append]
"""
import argparse
import re
import sys
import unicodedata
from datetime import datetime

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.fetchers.web_tree_fetcher import WebTreeFetcher
from app.models import Fetcher, Publisher, Resource, ResourceCandidate, ResourceParam
from app.services.grouping.inferer import infer

ROOT = "https://transparencia.jerez.es/infopublica/economica"
PATH_PREFIX = "/infopublica/economica"
INCLUDE = ["/a07-economica/"]
CRAWLER_NAME = "Jerez — Económica (crawler Web Tree)"

# Patrones (sobre path_template) de los hijos TABLA_REAL según la auditoría
# 2026-06 (docs/AUDITORIA_jerez_hijos.md). Editar aquí cuando haya recetas o
# nuevas series tabulares.
EXTRAER = [
    "03-ejecucionAyto",
    "c-deuda/{year}/deuda",
    "ContratosMenores_Publicidad",
    "Ejecucion_Gastos",
    "Plan_de_ajuste",
]


def slug(texto: str, maxlen: int = 48) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", "_", t).strip("_").lower()
    return t[:maxlen] or "recurso"


def asegurar_publisher(db) -> Publisher:
    pub = db.query(Publisher).filter(Publisher.nombre.ilike("%jerez%")).first()
    if pub is None:
        pub = Publisher(acronimo="JEREZ", nombre="Ayuntamiento de Jerez de la Frontera",
                        nivel="LOCAL", pais="ES")
        db.add(pub); db.flush()
    return pub


def asegurar_crawler(db, fetcher, pub) -> Resource:
    cr = db.query(Resource).filter(Resource.name == CRAWLER_NAME,
                                   Resource.deleted_at.is_(None)).first()
    if cr is None:
        cr = Resource(name=CRAWLER_NAME, fetcher_id=fetcher.id, publisher_id=pub.id,
                      target_table="_crawler_jerez_economica", active=True,
                      parent_resource_id=None, auto_generated=False)
        db.add(cr); db.flush()
        for k, v in {"root_url": ROOT, "path_prefix": PATH_PREFIX,
                     "include_patterns": str(INCLUDE).replace("'", '"')}.items():
            db.add(ResourceParam(resource_id=cr.id, key=k, value=v))
        db.flush()
    return cr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--append", action="store_true",
                    help="no retirar el descubrimiento anterior (por defecto, re-descubrir lo reemplaza)")
    ap.add_argument("--max-depth", type=int, default=2)
    args = ap.parse_args()

    db = SessionLocal()
    try:
        fetcher_row = db.query(Fetcher).filter(Fetcher.code == "Web Tree").first()
        if fetcher_row is None:
            raise SystemExit("No existe la especie 'Web Tree' (ejecuta seed_fetchers.py)")
        pub = asegurar_publisher(db)
        crawler = asegurar_crawler(db, fetcher_row, pub)
        db.commit()

        if not args.append:
            hijos = db.query(Resource).filter(Resource.parent_resource_id == crawler.id,
                                              Resource.deleted_at.is_(None)).all()
            marca = datetime.utcnow().strftime("%y%m%d%H%M%S")
            # sanear también retirados de pasadas antiguas que conserven su nombre
            # (la restricción única incluye a los borrados)
            zombis = db.query(Resource).filter(Resource.parent_resource_id == crawler.id,
                                               Resource.deleted_at.isnot(None),
                                               ~Resource.name.like("%~%")).all()
            for h in hijos + zombis:
                h.deleted_at = h.deleted_at or datetime.utcnow()
                # la unicidad de name/target_table es global (incluye retirados):
                # liberar los identificadores para el nuevo descubrimiento
                h.name = f"{h.name[:85]}~{marca}"
                h.target_table = f"{h.target_table[:50]}_{marca}"
            for c in db.query(ResourceCandidate).filter(ResourceCandidate.crawler_resource_id == crawler.id).all():
                c.deleted_at = datetime.utcnow()
            db.commit()
            print(f"[reset] {len(hijos)} hijos y sus candidatos retirados")

        # 2. Descubrir + inferir
        print(f"[discover] crawleando {ROOT} (depth {args.max_depth})...")
        wt = WebTreeFetcher({"root_url": ROOT, "crawl_mode": "discover",
                             "max_depth": args.max_depth, "page_delay": 0.0,
                             "crawl_timeout": 20, "path_prefix": PATH_PREFIX,
                             "include_patterns": INCLUDE})
        hojas = wt.discover()
        props = infer(hojas)
        print(f"[infer] {len(hojas)} hojas → {len(props)} propuestas")

        # variantes
        from app.models import FetcherPreset
        v_censo = db.query(FetcherPreset).filter(FetcherPreset.code == "Censo documental").first()
        v_datos = db.query(FetcherPreset).filter(FetcherPreset.code == "Extracción de datos").first()
        if not (v_censo and v_datos):
            raise SystemExit("Faltan las variantes Web Tree (ejecuta seed_fetchers.py)")

        # 3a. EL recurso-directorio: candidata con TODAS las hojas, variante Censo
        cand_dir = ResourceCandidate(
            crawler_resource_id=crawler.id,
            path_template=ROOT + "/{*}",
            dimensions=[], matched_urls=[h["url"] for h in hojas],
            file_types={}, suggested_name="Directorio documental (censo completo)",
            confidence=1.0, status="discovered",
        )
        db.add(cand_dir); db.flush()
        directorio = Resource(
            name="Jerez — Económica — Directorio documental (censo)",
            fetcher_id=crawler.fetcher_id, publisher_id=crawler.publisher_id,
            target_table="jerez_economica_directorio", active=True,
            enable_load=False, load_mode="upsert",
            parent_resource_id=crawler.id, auto_generated=True,
            preset_id=v_censo.id,
        )
        db.add(directorio); db.flush()
        db.add(ResourceParam(resource_id=directorio.id, key="root_url", value=ROOT))
        cand_dir.status = "promoted"
        cand_dir.promoted_resource_id = directorio.id
        cand_dir.reviewed_at = datetime.utcnow()
        cand_dir.reviewed_by = "jerez_webtree.py"
        print(f"[promote] directorio-censo: 1 recurso con {len(hojas)} ficheros")

        # 3b. Persistir candidatas; promover en 'datos' SOLO las TABLA_REAL
        creados = 0
        usados = {directorio.target_table}
        for p in props:
            extraer = any(pat in p.path_template for pat in EXTRAER)
            cand = ResourceCandidate(
                crawler_resource_id=crawler.id,
                path_template=p.path_template, dimensions=p.dimensions,
                matched_urls=p.matched_urls, file_types=p.file_types,
                suggested_name=p.suggested_name, confidence=p.confidence,
                status="discovered",
            )
            db.add(cand); db.flush()
            if not extraer:
                continue  # queda como candidata 'discovered'; el censo ya la cubre

            nombre = f"Jerez — {p.suggested_name}"[:96]
            base = slug(p.suggested_name)
            tt = f"jerez_{base}"
            n = 1
            while tt in usados or nombre in usados:
                n += 1
                tt = f"jerez_{base}_{n}"
                nombre = f"{f'Jerez — {p.suggested_name}'[:92]} #{n}"
            usados.add(tt); usados.add(nombre)

            child = Resource(
                name=nombre, fetcher_id=crawler.fetcher_id, publisher_id=crawler.publisher_id,
                target_table=tt, active=True, enable_load=False, load_mode="upsert",
                parent_resource_id=crawler.id, auto_generated=True,
                preset_id=v_datos.id,
            )
            db.add(child); db.flush()
            db.add(ResourceParam(resource_id=child.id, key="root_url", value=ROOT))
            cand.status = "promoted"
            cand.promoted_resource_id = child.id
            cand.reviewed_at = datetime.utcnow()
            cand.reviewed_by = "jerez_webtree.py"
            creados += 1
        db.commit()

        print(f"[promote] {creados} hijos en 'Extracción de datos' (TABLA_REAL de la auditoría) "
              f"+ 1 directorio-censo, bajo '{CRAWLER_NAME}'. "
              f"{len(props) - creados} propuestas quedan como candidatas (cubiertas por el censo).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
