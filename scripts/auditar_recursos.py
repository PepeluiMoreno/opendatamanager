"""Auditoría de coherencia de Resources (solo lectura).

Da la foto real de la BD y señala lo que el código actual ya no contempla, para
decidir la limpieza con datos en la mano. NO modifica nada.

Reporta:
  1. Recursos por especie (fetcher), separando vivos y apuntando a fetchers
     soft-deleted (resto de renombrados/retirados).
  2. Web Tree: colecciones (madre, sin padre) vs miembros (hijos promovidos),
     con candidatos pendientes/total y nº de hijos por colección.
  3. Solapamiento entre coleccciones: candidatos cuya URL aparece en más de un
     crawler (descubrimiento duplicado).
  4. Candidatos huérfanos (crawler inexistente o borrado).
  5. Recursos legacy por patrón de nombre/target_table (trío PDF_TABLE de Jerez).
  6. Resumen por origin (seed/ui/manifest) y estado_aprobacion si la columna existe.

Uso (en el contenedor app):
    docker cp scripts/auditar_recursos.py odmgr_app:/app/scripts/
    docker exec -it odmgr_app python scripts/auditar_recursos.py
"""
from __future__ import annotations

import os
import sys
from collections import Counter, defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.database import SessionLocal
from app.models import Fetcher, Resource, ResourceCandidate


def _val(obj, attr, default=None):
    return getattr(obj, attr, default)


def main() -> int:
    db = SessionLocal()
    try:
        fetchers = {f.id: f for f in db.query(Fetcher).all()}
        vivos = {fid: f for fid, f in fetchers.items() if f.deleted_at is None}

        resources = db.query(Resource).filter(Resource.deleted_at == None).all()
        print(f"\n=== Recursos vivos: {len(resources)} ===")

        # 1) Por especie + detección de fetcher soft-deleted
        por_especie = Counter()
        legacy_fetcher = []
        for r in resources:
            f = fetchers.get(r.fetcher_id)
            code = f.code if f else "<fetcher inexistente>"
            por_especie[code] += 1
            if f is None or f.deleted_at is not None:
                legacy_fetcher.append((r.name, code))
        print("\n-- Por especie --")
        for code, n in por_especie.most_common():
            print(f"   {n:4d}  {code}")
        if legacy_fetcher:
            print(f"\n  ⚠ {len(legacy_fetcher)} recurso(s) apuntan a una especie inexistente/retirada:")
            for nombre, code in legacy_fetcher:
                print(f"     - {nombre}  → {code}")

        # 2) Web Tree: colecciones vs miembros
        wt = [r for r in resources if (fetchers.get(r.fetcher_id) and fetchers[r.fetcher_id].code == "Web Tree")]
        madres = [r for r in wt if r.parent_resource_id is None]
        hijos = [r for r in wt if r.parent_resource_id is not None]
        print(f"\n=== Web Tree: {len(wt)} (colecciones-madre: {len(madres)}, miembros/hijos: {len(hijos)}) ===")

        cand_por_crawler = defaultdict(lambda: {"pendientes": 0, "total": 0})
        for c in db.query(ResourceCandidate).all():
            cid = c.crawler_resource_id
            cand_por_crawler[cid]["total"] += 1
            if getattr(c, "status", None) == "discovered":
                cand_por_crawler[cid]["pendientes"] += 1
        hijos_por_madre = Counter(r.parent_resource_id for r in hijos)

        print("\n-- Colecciones (recurso-madre) --")
        for r in madres:
            cc = cand_por_crawler.get(r.id, {"pendientes": 0, "total": 0})
            gc = _val(r, "genera_colecciones", "n/a")
            print(f"   • {r.name}")
            print(f"       candidatos pend/total: {cc['pendientes']}/{cc['total']} | miembros: {hijos_por_madre.get(r.id,0)}"
                  f" | genera_colecciones: {gc} | activo: {r.active}")

        # 3) Solapamiento de candidatos por URL entre crawlers
        url_a_crawlers = defaultdict(set)
        for c in db.query(ResourceCandidate).all():
            url = getattr(c, "url", None) or getattr(c, "sample_url", None)
            if url:
                url_a_crawlers[url].add(c.crawler_resource_id)
        solapados = {u: cs for u, cs in url_a_crawlers.items() if len(cs) > 1}
        if solapados:
            pares = Counter()
            for cs in solapados.values():
                ids = sorted(str(x) for x in cs)
                pares[tuple(ids)] += 1
            print(f"\n  ⚠ {len(solapados)} URL(s) descubiertas por más de un crawler (descubrimiento solapado):")
            nombre = {str(r.id): r.name for r in madres}
            for ids, n in pares.most_common(10):
                etq = " + ".join(nombre.get(i, i[:8]) for i in ids)
                print(f"     {n:5d}  {etq}")

        # 4) Candidatos huérfanos
        ids_vivos = {r.id for r in resources}
        huerfanos = [cid for cid in cand_por_crawler if cid not in ids_vivos]
        if huerfanos:
            print(f"\n  ⚠ {len(huerfanos)} crawler(s) con candidatos pero sin recurso vivo (huérfanos).")

        # 5) Legacy por patrón
        patrones = ("PMP", "Morosidad", "Deuda")
        sospechosos = [r for r in resources
                       if (fetchers.get(r.fetcher_id) and fetchers[r.fetcher_id].code != "Web Tree")
                       and any(p.lower() in (r.name or "").lower() for p in patrones)]
        if sospechosos:
            print(f"\n  ⚠ {len(sospechosos)} recurso(s) tipo no-WebTree con nombre PMP/Morosidad/Deuda (posible trío viejo):")
            for r in sospechosos:
                f = fetchers.get(r.fetcher_id)
                print(f"     - {r.name}  [{f.code if f else '?'}]  tabla={_val(r,'target_table')}")

        # 6) Resumen por origin / estado
        print("\n-- Por origin --")
        for k, n in Counter(_val(r, "origin", "?") for r in resources).most_common():
            print(f"   {n:4d}  {k}")
        if any(hasattr(r, "estado_aprobacion") for r in resources[:1]):
            print("-- Por estado_aprobacion --")
            for k, n in Counter(_val(r, "estado_aprobacion", "?") for r in resources).most_common():
                print(f"   {n:4d}  {k}")

        print("\n(Solo lectura: no se ha modificado nada.)\n")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
