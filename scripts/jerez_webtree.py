"""Crea todos los recursos posibles para el portal económico de Jerez vía Web Tree.

Ciclo completo end-to-end (el que en producción harían el crawler + Discovering.vue):
  1. Asegura el publisher de Jerez y un Resource crawler padre 'Web Tree' acotado
     a la sección económica (a07-economica).
  2. discover() recorre el árbol y GroupingInferer.infer() propone agrupaciones
     (series limpias + bundles por carpeta).
  3. Persiste cada propuesta como ResourceCandidate (status discovered).
  4. Promueve cada candidata a un Resource hijo (auto_generated), enlazando
     promoted_resource_id — exactamente lo que hace la mutation promote_candidate.

Idempotente por --reset: con --reset retira (soft-delete) los hijos y candidatos
previos del crawler antes de volver a descubrir. Sin --reset, solo promueve las
candidatas aún sin promover.

Uso:  DATABASE_URL=... python scripts/jerez_webtree.py [--reset] [--max-depth 2]
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
    ap.add_argument("--reset", action="store_true")
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

        if args.reset:
            hijos = db.query(Resource).filter(Resource.parent_resource_id == crawler.id).all()
            for h in hijos:
                h.deleted_at = datetime.utcnow()
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

        # 3+4. Persistir candidatas y promoverlas
        creados = 0
        usados = set()
        for p in props:
            cand = ResourceCandidate(
                crawler_resource_id=crawler.id,
                path_template=p.path_template, dimensions=p.dimensions,
                matched_urls=p.matched_urls, file_types=p.file_types,
                suggested_name=p.suggested_name, confidence=p.confidence,
                status="discovered",
            )
            db.add(cand); db.flush()

            nombre = f"Jerez — {p.suggested_name}"[:100]
            base = slug(p.suggested_name)
            tt = f"jerez_{base}"
            n = 1
            while tt in usados:
                n += 1; tt = f"jerez_{base}_{n}"
            usados.add(tt)

            child = Resource(
                name=nombre, fetcher_id=crawler.fetcher_id, publisher_id=crawler.publisher_id,
                target_table=tt, active=True, enable_load=False, load_mode="upsert",
                parent_resource_id=crawler.id, auto_generated=True,
            )
            db.add(child); db.flush()
            db.add(ResourceParam(resource_id=child.id, key="root_url", value=ROOT))
            cand.status = "promoted"
            cand.promoted_resource_id = child.id
            cand.reviewed_at = datetime.utcnow()
            cand.reviewed_by = "jerez_webtree.py"
            creados += 1
        db.commit()

        series = sum(1 for p in props if not p.path_template.endswith("{*}"))
        bundles = len(props) - series
        print(f"[promote] {creados} recursos hijos creados ({series} series, {bundles} bundles) "
              f"bajo el crawler '{CRAWLER_NAME}'")
    finally:
        db.close()


if __name__ == "__main__":
    main()
