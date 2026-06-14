"""CatalogFetcher — Nave nodriza de catálogo (descubridor DCAT).

Consulta un catálogo de datos abiertos (por defecto la apidata de datos.gob.es,
DCAT-AP-ES) y emite UN CANDIDATO POR DISTRIBUCIÓN descargable que pase la regla
de selección. Cada candidato es autodescriptivo: lleva la especie-destino del
hijo (`target_fetcher_code`) y sus params (`target_params`: url + format), de modo
que la promoción es genérica y el hijo EXTRAE con otra especie que la del padre.

Modos: ["extraer", "descubrir"].
  · descubrir → propose(): el manager crea ResourceCandidate por propuesta.
  · extraer   → stream()/fetch(): vuelca el listado del catálogo como dataset
    (útil para auditar la cosecha del catálogo en sí).

No normaliza ni puntúa: ODM es productor neutral. La regla de selección es un
filtro de PERTINENCIA del catálogo (qué datasets son registros de interés), no
lógica de consumidor.

Params principales:
  catalog_api        Base de la apidata (def. https://datos.gob.es/apidata)
  query_terms        Palabras de título a consultar, separadas por coma
                     (def. "asociaciones,fundaciones"). Una consulta por término.
  page_size          Tamaño de página de la apidata (def. 50)
  max_pages          Límite de páginas por término (def. 20)
  title_include      Regex (i) que el título DEBE casar (def. registros)
  title_exclude      Regex (i) que descarta el dataset (ruido)
  formats            Formatos de distribución admitidos, coma (def. "csv,json")
  drop_url_contains  Subcadenas que descartan una distribución (def.
                     "diccionario,diccionario_datos" — los diccionarios de datos)
  child_fetcher      Especie-destino de los hijos (def. "File Download")
"""
import json
import logging
import re
from typing import Any, Dict, Generator, List, Optional

from app.fetchers.base import BaseFetcher, RawData, ParsedData, DomainData

logger = logging.getLogger(__name__)

_DEFAULT_INCLUDE = r"(registro\s+de\s+(asociaciones|fundaciones)|^(asociaciones|fundaciones)\s+de\b|^registros?\s+de\s+fundaciones)"
_DEFAULT_EXCLUDE = (
    r"(paciente|juvenil|profesional|estad[íi]stic|cuentas|puesto|consumidor|"
    r"empresarial|desarrollo\s+rural|p[úu]blic[ao]s?\b|inventario|localizaci|"
    r"econ[óo]mic|ámbito|servicio\s+wms|legislatura|balance)"
)


class CatalogFetcher(BaseFetcher):

    def _cfg(self) -> Dict[str, Any]:
        p = self.params
        return {
            "api": (p.get("catalog_api") or "https://datos.gob.es/apidata").rstrip("/"),
            "type": (p.get("catalog_type") or "datosgob").strip().lower(),
            "terms": [t.strip() for t in (p.get("query_terms") or "asociaciones,fundaciones").split(",") if t.strip()],
            "page_size": int(p.get("page_size", 50)),
            "max_pages": int(p.get("max_pages", 20)),
            "include": re.compile(p.get("title_include") or _DEFAULT_INCLUDE, re.I),
            "exclude": re.compile(p.get("title_exclude") or _DEFAULT_EXCLUDE, re.I),
            "formats": {f.strip().lower() for f in (p.get("formats") or "csv,json").split(",") if f.strip()},
            "drop": [s.strip().lower() for s in (p.get("drop_url_contains") or "diccionario").split(",") if s.strip()],
            "child": p.get("child_fetcher") or "File Download",
            "prefer": [f.strip().lower() for f in (p.get("prefer_format") or "").split(",") if f.strip()],
        }

    # ── helpers de extracción DCAT (apidata datos.gob.es) ────────────────────
    @staticmethod
    def _val(node: Any) -> Optional[str]:
        """Extrae el valor 'es' de un campo multilingüe DCAT (_value/_lang)."""
        if isinstance(node, list):
            for x in node:
                if isinstance(x, dict) and x.get("_lang") in ("es", None):
                    return x.get("_value")
            return node[0].get("_value") if node and isinstance(node[0], dict) else None
        if isinstance(node, dict):
            return node.get("_value")
        return node

    @staticmethod
    def _fmt(dist: Dict[str, Any]) -> str:
        f = dist.get("format", {})
        v = f.get("value") if isinstance(f, dict) else f
        return str(v or "").split("/")[-1].lower()

    def _fetch_page(self, api: str, term: str, page: int, size: int) -> List[Dict]:
        url = f"{api}/catalog/dataset/title/{term}"
        resp = self._request(None, "GET", url,
                             params={"_pageSize": size, "_page": page},
                             headers={"Accept": "application/json"},
                             timeout=int(self.params.get("timeout", 30)))
        resp.raise_for_status()
        data = resp.json()
        res = data.get("result", {})
        return res.get("items", []) if isinstance(res, dict) else (res or [])

    def _iter_datasets(self, cfg: Dict) -> Generator[Dict, None, None]:
        for term in cfg["terms"]:
            for page in range(cfg["max_pages"]):
                try:
                    items = self._fetch_page(cfg["api"], term, page, cfg["page_size"])
                except Exception as exc:
                    logger.error(f"[catalog] término '{term}' pág {page}: {exc}")
                    break
                if not items:
                    break
                for it in items:
                    yield it
                if len(items) < cfg["page_size"]:
                    break

    def _iter_datasets_ckan(self, cfg: Dict) -> Generator[Dict, None, None]:
        """Pagina package_search de un portal CKAN (api = base del portal)."""
        base = cfg["api"]
        for term in cfg["terms"]:
            start = 0
            for _ in range(cfg["max_pages"]):
                try:
                    resp = self._request(None, "GET", f"{base}/api/3/action/package_search",
                                         params={"q": term, "rows": cfg["page_size"], "start": start},
                                         headers={"Accept": "application/json"},
                                         timeout=int(self.params.get("timeout", 30)))
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as exc:
                    logger.error(f"[catalog/ckan] término '{term}' start {start}: {exc}")
                    break
                if not data.get("success"):
                    break
                results = (data.get("result") or {}).get("results") or []
                if not results:
                    break
                for pkg in results:
                    yield pkg
                start += len(results)
                if len(results) < cfg["page_size"]:
                    break

    @staticmethod
    def _rdf_fmt(v) -> str:
        """Normaliza un dct:format / dcat:mediaType (URI o literal) a etiqueta corta."""
        if not v:
            return ""
        s = str(v).strip().lower().rstrip("/")
        s = s.split("/")[-1].split("#")[-1]
        for k in ("geojson", "xlsx", "csv", "xls", "json", "xml", "zip", "rdf", "ttl", "kml"):
            if k in s:
                return k
        return s

    def _iter_datasets_rdf(self, cfg: Dict) -> Generator[Dict, None, None]:
        """Recorre un catálogo DCAT-AP servido como RDF (RDF/XML, Turtle o JSON-LD).
        `catalog_api` es la URL del feed. Sigue paginación hydra:next si la hay.
        Mismo contrato que las otras variantes: produce {title, publisher, dists}
        donde dists son tuplas (url, formato, etiqueta)."""
        import rdflib
        from rdflib.namespace import RDF
        DCAT = rdflib.Namespace("http://www.w3.org/ns/dcat#")
        DCT = rdflib.Namespace("http://purl.org/dc/terms/")
        FOAF = rdflib.Namespace("http://xmlns.com/foaf/0.1/")
        HYDRA = rdflib.Namespace("http://www.w3.org/ns/hydra/core#")
        url = cfg["api"]
        visited: set = set()
        for _ in range(cfg["max_pages"]):
            if not url or url in visited:
                break
            visited.add(url)
            try:
                resp = self._request(None, "GET", url,
                                     headers={"Accept": "application/rdf+xml, text/turtle, application/ld+json;q=0.9"},
                                     timeout=int(self.params.get("timeout", 60)))
                resp.raise_for_status()
                raw = resp.content
            except Exception as exc:
                logger.error(f"[catalog/rdf] {url}: {exc}")
                break
            g = rdflib.Graph()
            parsed = False
            for fmt in ("xml", "turtle", "json-ld", "nt"):
                try:
                    g.parse(data=raw, format=fmt)
                    parsed = True
                    break
                except Exception:
                    continue
            if not parsed:
                logger.error(f"[catalog/rdf] no se pudo parsear RDF de {url}")
                break

            def _lit(subj, pred):
                best = None
                for o in g.objects(subj, pred):
                    if isinstance(o, rdflib.Literal):
                        if (o.language or "es") == "es":
                            return str(o)
                        best = best or str(o)
                    else:
                        best = best or str(o)
                return best

            for ds in g.subjects(RDF.type, DCAT.Dataset):
                title = _lit(ds, DCT.title) or ""
                pub = ""
                pnode = g.value(ds, DCT.publisher)
                if pnode is not None:
                    pub = _lit(pnode, FOAF.name) or str(pnode).rstrip("/").split("/")[-1]
                dists = []
                for dist in g.objects(ds, DCAT.distribution):
                    du = g.value(dist, DCAT.downloadURL) or g.value(dist, DCAT.accessURL)
                    fmt = g.value(dist, DCT["format"]) or g.value(dist, DCAT.mediaType)
                    label = _lit(dist, DCT.title) or (str(du).rstrip("/").split("/")[-1].split("?")[0] if du else "")
                    dists.append((str(du) if du else None, self._rdf_fmt(fmt), label))
                yield {"title": title, "publisher": pub, "dists": dists}

            nxt = None
            for o in g.objects(None, HYDRA.next):
                nxt = str(o)
                break
            url = nxt

    def _consider(self, title: str, publisher: str, dist_iter, cfg: Dict,
                  seen: set, out: List[Dict[str, Any]]) -> None:
        """Filtro de pertinencia común a DCAT y CKAN. `dist_iter` produce
        tuplas (url, format, dist_label)."""
        if not title or not cfg["include"].search(title) or cfg["exclude"].search(title):
            return
        for url, fmt, dlabel in dist_iter:
            if not url or fmt not in cfg["formats"]:
                continue
            low = url.lower()
            if any(s in low for s in cfg["drop"]):
                continue
            if url in seen:
                continue
            # El exclude también se aplica a la etiqueta de la distribución: un
            # registro puede traer distribuciones que NO lo son (Balance, Cuentas...).
            if dlabel and cfg["exclude"].search(dlabel):
                continue
            seen.add(url)
            out.append({"title": title.strip(), "publisher": publisher or "",
                        "url": url, "format": fmt, "dist_label": dlabel})

    def _entries(self) -> List[Dict[str, Any]]:
        """Devuelve las entradas pertinentes: (title, publisher, url, format).
        Soporta dos catálogos: la apidata de datos.gob.es (DCAT-AP-ES) y CKAN."""
        cfg = self._cfg()
        seen: set = set()
        out: List[Dict[str, Any]] = []

        if cfg["type"] == "ckan":
            for pkg in self._iter_datasets_ckan(cfg):
                title = pkg.get("title") or pkg.get("name") or ""
                org = pkg.get("organization") or {}
                publisher = (org.get("title") or org.get("name") or "") if isinstance(org, dict) else ""
                def _ckan_dists(resources):
                    for r in resources or []:
                        u = r.get("url")
                        fmt = str(r.get("format") or "").strip().lower()
                        dl = r.get("name") or (u.rstrip("/").split("/")[-1].split("?")[0] if u else "")
                        yield u, fmt, dl
                self._consider(title, publisher, _ckan_dists(pkg.get("resources")), cfg, seen, out)
        elif cfg["type"] in ("dcat-rdf", "rdf"):
            for ds in self._iter_datasets_rdf(cfg):
                self._consider(ds["title"], ds["publisher"], iter(ds["dists"]), cfg, seen, out)
        else:
            for it in self._iter_datasets(cfg):
                title = self._val(it.get("title")) or ""
                publisher = it.get("publisher", "")
                publisher = publisher.split("/")[-1] if isinstance(publisher, str) else ""
                dists = it.get("distribution", []) or []
                if isinstance(dists, dict):
                    dists = [dists]
                def _dcat_dists(distribs):
                    for d in distribs:
                        if not isinstance(d, dict):
                            continue
                        url = d.get("downloadURL") or d.get("accessURL")
                        dl = self._val(d.get("title")) or (url.rstrip("/").split("/")[-1].split("?")[0] if url else "")
                        yield url, self._fmt(d), dl
                self._consider(title, publisher, _dcat_dists(dists), cfg, seen, out)

        logger.info(f"[catalog] {len(out)} distribución(es) pertinente(s) tras filtro.")
        if cfg["prefer"]:
            out = self._collapse_formats(out, cfg["prefer"])
            logger.info(f"[catalog] {len(out)} tras prefer_format={cfg['prefer']}.")
        return out

    @staticmethod
    def _collapse_formats(entries: List[Dict[str, Any]], prefer: List[str]) -> List[Dict[str, Any]]:
        """Cuando un mismo registro (title, publisher) se publica en varios formatos,
        deja solo el preferido. Si el preferido no está en el grupo, no descarta nada.
        Conserva TODAS las entradas del formato elegido (p. ej. un fichero por
        provincia): solo elimina los formatos redundantes, nunca particiones."""
        from collections import defaultdict
        grupos: Dict[Any, List[Dict]] = defaultdict(list)
        for e in entries:
            grupos[(e["title"], e["publisher"])].append(e)
        out: List[Dict[str, Any]] = []
        for items in grupos.values():
            formatos = {i["format"] for i in items}
            elegido = next((f for f in prefer if f in formatos), None)
            if elegido is None:
                out.extend(items)
            else:
                out.extend(i for i in items if i["format"] == elegido)
        return out

    # ── modo DESCUBRIR ───────────────────────────────────────────────────────
    def propose(self) -> List[Dict[str, Any]]:
        cfg = self._cfg()
        proposals = []
        for e in self._entries():
            name = e["title"]
            if e["publisher"]:
                name = f"{name} [{e['publisher']}]"
            dl = e.get("dist_label")
            if dl and dl.lower() not in name.lower():
                name = f"{name} · {dl}"
            proposals.append({
                "suggested_name": name[:200],
                "matched_urls": [e["url"]],
                "file_types": {e["format"]: 1},
                "confidence": 0.9,
                "target_fetcher_code": cfg["child"],
                "target_params": {"url": e["url"], "format": e["format"]},
            })
        self.profile_stats = {"total_files": len(proposals),
                              "file_extensions": {p["format"]: 1 for p in [
                                  {"format": list(x["file_types"].keys())[0]} for x in proposals]}}
        return proposals

    # ── modo EXTRAER ─────────────────────────────────────────────────────────
    def stream(self) -> Generator[List[Dict[str, Any]], None, None]:
        yield self._entries()

    def fetch(self) -> RawData:
        out: List[Dict] = []
        for chunk in self.stream():
            out.extend(chunk)
        return out

    def parse(self, raw: RawData) -> ParsedData:
        return raw

    def normalize(self, parsed: ParsedData) -> DomainData:
        return parsed
