"""Auditoría de contenido de los hijos Web Tree: ¿qué dato produce cada uno HOY?

Para cada Resource hijo promovido, descarga UN fichero de muestra de su
candidata (el más reciente por año) y clasifica el resultado del parseo
compartido (el mismo de File Download):

  - TABLA_REAL          ≥2 columnas con nombre real y ≥5 filas pobladas:
                        el parseo genérico ya produce un dataset útil.
  - INFORME_FORMULARIO  filas-basura (columnas unnamed, celdas vacías):
                        necesita receta de extracción dirigida (decisión §8b).
  - PILA_DOCUMENTAL     sin filas aprovechables o bundle heterogéneo:
                        su valor es el censo/registro (decisión §8a, insumo §9).

Genera docs/AUDITORIA_jerez_hijos.md con el detalle y un resumen cuantificado.

Uso:  python scripts/auditoria_contenido_webtree.py [--paralelo 3] [--max-mb 8]
"""
import argparse
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.fetchers.web_tree_fetcher import WebTreeFetcher
from app.models import Resource, ResourceCandidate

META = {"_source_file_url", "_source_file_name", "_source_format",
        "year", "month", "quarter", "code", "date"}
_YEAR_RE = re.compile(r"(19|20)\d{2}")


def url_muestra(urls):
    """El fichero más reciente (año máximo en la URL); a igualdad, el último."""
    def año(u):
        años = [int(m.group(0)) for m in _YEAR_RE.finditer(u)]
        return max(años) if años else 0
    return sorted(urls, key=año)[-1]


def clasificar(filas, file_types):
    if not filas:
        return "PILA_DOCUMENTAL", "el parseo no produjo filas"
    cols = set()
    for f in filas:
        cols.update(f.keys())
    cols -= META
    con_nombre = [c for c in cols if not str(c).startswith("unnamed")]
    n = len(filas)
    # ratio de celdas pobladas en las columnas de datos
    total = sum(1 for f in filas for c in cols)
    llenas = sum(1 for f in filas for c in cols if str(f.get(c, "")).strip())
    ratio = (llenas / total) if total else 0.0
    if len(con_nombre) >= 2 and n >= 5 and ratio >= 0.4:
        return "TABLA_REAL", f"{n} filas, {len(con_nombre)} columnas con nombre, {ratio:.0%} pobladas"
    if len(file_types or {}) > 1:
        return "PILA_DOCUMENTAL", f"bundle heterogéneo {dict(file_types)}; muestra: {n} filas, {ratio:.0%} pobladas"
    return "INFORME_FORMULARIO", f"{n} filas, {len(con_nombre)} col. con nombre, {ratio:.0%} pobladas"


def auditar_uno(nombre, candidato, max_mb, timeout):
    url = url_muestra(candidato.matched_urls)
    es_bundle = candidato.path_template.endswith("{*}")
    f = WebTreeFetcher({"root_url": "https://transparencia.jerez.es",
                        "max_file_mb": max_mb, "download_timeout": timeout})
    try:
        filas = f._download_and_parse(url)
    except Exception as exc:  # noqa: BLE001 — el fallo es un dato de la auditoría
        return {"nombre": nombre, "clase": "PILA_DOCUMENTAL",
                "detalle": f"descarga/parseo falló: {type(exc).__name__}: {str(exc)[:80]}",
                "url": url, "urls": len(candidato.matched_urls), "bundle": es_bundle}
    clase, detalle = clasificar(filas, candidato.file_types)
    return {"nombre": nombre, "clase": clase, "detalle": detalle,
            "url": url, "urls": len(candidato.matched_urls), "bundle": es_bundle}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paralelo", type=int, default=3)
    ap.add_argument("--max-mb", type=int, default=8)
    ap.add_argument("--timeout", type=int, default=40)
    ap.add_argument("--checkpoint", default="/tmp/auditoria_ckpt.json")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        pares = []
        for r in (db.query(Resource)
                  .filter(Resource.parent_resource_id.isnot(None),
                          Resource.deleted_at.is_(None),
                          Resource.auto_generated.is_(True)).all()):
            c = (db.query(ResourceCandidate)
                 .filter(ResourceCandidate.promoted_resource_id == r.id,
                         ResourceCandidate.deleted_at.is_(None))
                 .order_by(ResourceCandidate.detected_at.desc()).first())
            if c and c.matched_urls:
                pares.append((r.name, c))
        print(f"[auditoría] {len(pares)} hijos con candidata")

        import json, os
        hechos = {}
        if os.path.exists(args.checkpoint):
            hechos = json.load(open(args.checkpoint))
            print(f"[auditoría] checkpoint: {len(hechos)} ya auditados, se reanuda")
        pares = [(n, c) for n, c in pares if n not in hechos]

        resultados = list(hechos.values())
        with ThreadPoolExecutor(max_workers=args.paralelo) as ex:
            futs = {ex.submit(auditar_uno, n, c, args.max_mb, args.timeout): n for n, c in pares}
            for i, fut in enumerate(as_completed(futs), 1):
                r = fut.result()
                resultados.append(r)
                hechos[r["nombre"]] = r
                json.dump(hechos, open(args.checkpoint, "w"))
                print(f"  [{i}/{len(pares)}] {r['clase']:18} {r['nombre'][:70]}")

        resultados.sort(key=lambda x: (x["clase"], -x["urls"]))
        cuenta = {}
        urls_por_clase = {}
        for r in resultados:
            cuenta[r["clase"]] = cuenta.get(r["clase"], 0) + 1
            urls_por_clase[r["clase"]] = urls_por_clase.get(r["clase"], 0) + r["urls"]

        lineas = [
            "# Auditoría de contenido — hijos Web Tree de Jerez",
            f"\nFecha: {datetime.utcnow():%Y-%m-%d %H:%M} UTC · {len(resultados)} hijos auditados",
            "(1 fichero de muestra por hijo, el más reciente; parseo compartido de File Download)\n",
            "## Resumen\n",
            "| Clase | Hijos | Ficheros que cubren | Significa |",
            "|---|---|---|---|",
        ]
        sig = {"TABLA_REAL": "el parseo actual ya produce dataset útil",
               "INFORME_FORMULARIO": "necesita receta de extracción dirigida (§8b)",
               "PILA_DOCUMENTAL": "su valor es el censo/registro (§8a, insumo CKAN §9)"}
        for cl in ("TABLA_REAL", "INFORME_FORMULARIO", "PILA_DOCUMENTAL"):
            lineas.append(f"| {cl} | {cuenta.get(cl, 0)} | {urls_por_clase.get(cl, 0)} | {sig[cl]} |")
        lineas.append("\n## Detalle\n")
        lineas.append("| Clase | Recurso | Ficheros | Muestra (diagnóstico) |")
        lineas.append("|---|---|---|---|")
        for r in resultados:
            tipo = "bundle" if r["bundle"] else "serie"
            lineas.append(f"| {r['clase']} | {r['nombre'][:80]} ({tipo}) | {r['urls']} | {r['detalle']} |")
        open("docs/AUDITORIA_jerez_hijos.md", "w", encoding="utf-8").write("\n".join(lineas) + "\n")
        print("\n[auditoría] resumen:", {k: v for k, v in sorted(cuenta.items())})
        print("[auditoría] informe en docs/AUDITORIA_jerez_hijos.md")
    finally:
        db.close()


if __name__ == "__main__":
    main()
