"""
AtomCrawlerFetcher — Crawler de servicios ATOM de descarga (INSPIRE / OpenSearch).

Espejo de WebTreeFetcher, pero el árbol no es HTML sino una jerarquía de feeds
ATOM: un Download Service predefinido (Catastro, IGN, cualquier IDE) cuyo feed de
servicio enlaza a feeds por territorio/gerencia que, a su vez, enlazan a los
ficheros descargables (GML/GZ/ZIP), normalmente uno por municipio.

Dual-modo, mismo contrato que Web Tree:

  · discover()  (recurso-madre, es_coleccion): recorre los feeds y devuelve las
    URLs hoja [{"url","file_type",...}]. El FetcherManager las pasa a infer(), que
    agrupa por path_template y detecta el código de municipio como dimensión ->
    UN candidato dimensionado por dataset. 8.000 ficheros NO son 8.000 recursos.

  · stream()    (recurso hijo promovido): recibe _matched_urls/_dimensions/
    _path_template inyectados por el manager y, por cada URL, DESCARGA el ZIP,
    extrae el `.gml` y lo parsea a registros con la MISMA maquinaria de
    `Compressed File` (`_extract_*` + `parse_structured_file(fmt="gml")` ->
    `gml_parser.parse_gml`). Cada registro se etiqueta con la dimensión (municipio,
    re-extraída del path_template). Salida homogénea (registros/JSONL), idéntica a
    cualquier otro recurso de ODM. El mapeo semántico es de SIPI, no de aquí.

No se duplica nada: la extracción y el parseo viven en `compressed_file` /
`file_parsers` / `gml_parser` (productor-neutro). Esta especie solo orquesta
"recorre el árbol" (discover) y "extrae cada hoja de la lista" (stream).

Agnóstico de dominio: distingue sub-feed de fichero por el type/extensión del
<link>; no sabe nada de Catastro ni de parcelas. Cortesía (rate_limit_per_second/
request_delay_ms/max_per_hour) vía self._request en ambos modos.
"""
from __future__ import annotations

import json
import logging
import re
import time
import xml.etree.ElementTree as ET
from collections import deque, defaultdict
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional
from urllib.parse import urlparse

from app.fetchers.base import BaseFetcher, RawData, ParsedData, DomainData
from app.fetchers.compressed_file import (
    _extract_zip, _extract_tar, _extract_gz, _extract_7z, _TAR_MODES,
)
from app.fetchers.file_parsers import infer_file_format, parse_structured_file

logger = logging.getLogger(__name__)

_DEFAULT_LEAF_EXTS = ("zip", "gz", "gml", "tar", "7z", "rar", "tgz")
_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
_SEP_SPLIT = re.compile(r"([-_.])")


def _localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower() if "}" in tag else tag.lower()


def _ext(href: str) -> str:
    last = urlparse(href).path.rsplit("/", 1)[-1]
    return last.rsplit(".", 1)[-1].lower() if "." in last else ""


class AtomCrawlerFetcher(BaseFetcher):

    # ── Config ────────────────────────────────────────────────────────────────
    def _as_list(self, v) -> List[str]:
        if not v:
            return []
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        s = str(v).strip()
        if s.startswith("["):
            try:
                return [str(x).strip() for x in json.loads(s) if str(x).strip()]
            except Exception:
                pass
        return [t.strip() for t in s.split(",") if t.strip()]

    def _cfg(self) -> Dict[str, Any]:
        p = self.params
        leaf_exts = self._as_list(p.get("leaf_exts")) or list(_DEFAULT_LEAF_EXTS)
        return {
            "url": p.get("url"),
            "filtro": self._as_list(p.get("filtro_incluir")),
            "leaf_exts": {e.lower().lstrip(".") for e in leaf_exts},
            "max_depth": int(p.get("max_depth", 0) or 0),
            "max_feeds": int(p.get("max_feeds", 500) or 500),
            "timeout": int(p.get("timeout", 60) or 60),
        }

    # ── DISCOVER (recurso-madre) ────────────────────────────────────────────────
    def _clasificar_link(self, href: str, type_attr: str, leaf_exts: set) -> Optional[str]:
        if not href:
            return None
        t = (type_attr or "").lower()
        ext = _ext(href)
        if ext in leaf_exts or "zip" in t or "gzip" in t or "octet-stream" in t:
            return "leaf"
        if "atom" in t or "rss" in t or ext in ("xml", "atom", "rss"):
            return "feed"
        return None

    def _links(self, entry: ET.Element):
        for el in entry.iter():
            ln = _localname(el.tag)
            if ln == "link":
                href = el.get("href") or (el.text or "").strip()
                if href:
                    yield href, el.get("type") or ""
            elif ln in ("enclosure", "url") and (el.get("url") or el.text):
                yield (el.get("url") or el.text or "").strip(), el.get("type") or ""

    def _clave(self, entry: ET.Element, href: str) -> str:
        partes = [href]
        for el in entry.iter():
            if _localname(el.tag) in ("title", "id") and el.text:
                partes.append(el.text.strip())
        return " ".join(partes)

    def discover(self, max_files: int = 0) -> List[Dict[str, Any]]:
        cfg = self._cfg()
        if not cfg["url"]:
            raise ValueError("AtomCrawlerFetcher.discover(): falta 'url' (feed de servicio).")

        visitados: set = set()
        cola: deque = deque([(cfg["url"], 0)])
        hojas: List[Dict[str, Any]] = []
        vistos: set = set()
        feeds = 0
        fuera = 0

        while cola:
            feed_url, depth = cola.popleft()
            if feed_url in visitados:
                continue
            visitados.add(feed_url)
            if feeds >= cfg["max_feeds"]:
                logger.warning(f"[atom-crawler] tope de feeds ({cfg['max_feeds']}); corto el descenso.")
                break

            resp = self._request(None, "GET", feed_url, timeout=cfg["timeout"])
            resp.raise_for_status()
            feeds += 1
            try:
                root = ET.fromstring(resp.text)
            except ET.ParseError as e:
                logger.warning(f"[atom-crawler] feed no parseable, lo salto: {feed_url} ({e})")
                continue

            forzar_hoja = cfg["max_depth"] > 0 and depth >= cfg["max_depth"]
            for entry in (el for el in root.iter() if _localname(el.tag) in ("entry", "item")):
                href_hoja = href_feed = None
                for href, type_attr in self._links(entry):
                    clase = "leaf" if forzar_hoja else self._clasificar_link(href, type_attr, cfg["leaf_exts"])
                    if clase == "leaf" and href_hoja is None:
                        href_hoja = href
                    elif clase == "feed" and href_feed is None:
                        href_feed = href
                if href_hoja:
                    if cfg["filtro"] and not any(s in self._clave(entry, href_hoja) for s in cfg["filtro"]):
                        fuera += 1
                        continue
                    if href_hoja in vistos:
                        continue
                    vistos.add(href_hoja)
                    hojas.append({"url": href_hoja, "file_type": _ext(href_hoja) or "zip",
                                  "source_feed": feed_url, "depth": depth + 1})
                    if max_files and len(hojas) >= max_files:
                        cola.clear()
                        break
                elif href_feed:
                    cola.append((href_feed, depth + 1))

        self.profile_stats = {
            "total_files": len(hojas),
            "feeds_leidos": feeds,
            "descartadas_por_filtro": fuera,
            "file_extensions": {ext: sum(1 for h in hojas if h["file_type"] == ext)
                                for ext in {h["file_type"] for h in hojas}},
        }
        logger.info(f"[atom-crawler] {feeds} feed(s), {len(hojas)} hoja(s); filtro fuera: {fuera}.")
        return hojas

    # ── PROPOSE (recurso-madre): un candidato YA FORMADO por PRODUCTOR ───────────
    #
    # discover()+infer() falla en feeds federados como el del Catastro: las URLs
    # hoja varían el código de municipio en DOS átomos correlacionados (la carpeta
    # `02001-ABENGIBRE` Y el código del filename `...CP.02001.zip`), y el infer
    # genérico —que colapsa de a un átomo— deja ~1 propuesta por municipio. Además
    # el feed nacional FEDERA varios productores (DGC peninsular + diputaciones
    # forales) con rutas y GML internos distintos.
    #
    # propose() resuelve ambas cosas sin tocar el infer global: agrupa las hojas
    # por PRODUCTOR (netloc + nº de segmentos), y por grupo construye él mismo el
    # path_template (constante donde no varía, {placeholder} donde sí) y las
    # dimensiones. Devuelve UN candidato autosuficiente por productor, con su
    # `target_fetcher_code`=Crawler ATOM y `target_params` (entry/inner_format/
    # cortesía) heredados —el `entry` del padre solo para el productor primario;
    # los federados, con GML único, usan `*.gml`.
    def propose(self) -> List[Dict[str, Any]]:
        hojas = self.discover()
        grupos: Dict[tuple, List[str]] = defaultdict(list)
        for h in hojas:
            p = urlparse(h["url"])
            nseg = len([s for s in p.path.split("/") if s])
            grupos[(p.netloc, nseg)].append(h["url"])

        proposals: List[Dict[str, Any]] = []
        for (netloc, _n), urls in grupos.items():
            path_template, dims = self._build_template(urls)
            ft: Dict[str, int] = defaultdict(int)
            for u in urls:
                ft[_ext(u) or "zip"] += 1
            proposals.append({
                "suggested_name": self._nombre(netloc, path_template)[:200],
                "path_template": path_template,
                "dimensions": dims,
                "matched_urls": sorted(urls),
                "file_types": dict(ft),
                "confidence": 0.9,
                "target_fetcher_code": "Crawler ATOM",
                "target_params": self._child_params(netloc),
            })
        proposals.sort(key=lambda p: -len(p["matched_urls"]))
        self.profile_stats = {
            "total_files": len(hojas),
            "productores": len(proposals),
            "file_extensions": {ext: sum(1 for h in hojas if h["file_type"] == ext)
                                for ext in {h["file_type"] for h in hojas}},
        }
        logger.info(f"[atom-crawler] propose: {len(hojas)} hoja(s) → {len(proposals)} productor(es).")
        return proposals

    # — helpers de propose ————————————————————————————————————————————————————
    @staticmethod
    def _dim_name(values: List[str], usados: set) -> str:
        """Nombre semántico para un átomo variable (heurística INSPIRE-ES).
        Garantiza unicidad sufijando _2, _3… si el nombre ya está en uso."""
        vs = [str(v) for v in values]
        if all(re.fullmatch(r"\d{2}", v) for v in vs):
            base = "provincia"
        elif all(re.fullmatch(r"\d{5}-.+", v) for v in vs):
            base = "municipio_nombre"
        elif all(re.fullmatch(r"\d{3,5}", v) for v in vs):
            base = "municipio"
        else:
            base = "codigo"
        name, k = base, 2
        while name in usados:
            name = f"{base}_{k}"
            k += 1
        usados.add(name)
        return name

    def _build_template(self, urls: List[str]) -> tuple:
        """Plantilla + dimensiones de un grupo de URLs hermanas (mismo netloc y
        nº de segmentos). Constante donde no varía; {dim} donde sí (en segmentos
        de path y, troceando por separadores, dentro del filename)."""
        parsed = [urlparse(u) for u in urls]
        scheme, netloc = parsed[0].scheme, parsed[0].netloc
        seg_lists = [[s for s in p.path.split("/") if s] for p in parsed]
        n = len(seg_lists[0])
        usados: set = set()
        template_segs: List[str] = []
        dims: List[Dict[str, Any]] = []
        for i in range(n):
            col = [segs[i] for segs in seg_lists]
            distintos = sorted(set(col))
            is_last = i == n - 1
            if not is_last:
                if len(distintos) == 1:
                    template_segs.append(col[0])
                else:
                    name = self._dim_name(col, usados)
                    template_segs.append("{" + name + "}")
                    dims.append({"name": name, "kind": "code", "segment_index": i,
                                 "in_filename": False, "sample_values": distintos[:20]})
                continue
            # último segmento = filename: trocear por separadores y alinear átomos
            atomized = [[a for a in _SEP_SPLIT.split(f) if a != ""] for f in col]
            L = len(atomized[0])
            if any(len(a) != L for a in atomized):
                # estructura irregular: un único placeholder por todo el filename
                name = self._dim_name(col, usados)
                template_segs.append("{" + name + "}")
                dims.append({"name": name, "kind": "code", "segment_index": i,
                             "in_filename": True, "sample_values": distintos[:20]})
                continue
            out: List[str] = []
            for j in range(L):
                acol = [a[j] for a in atomized]
                if len(set(acol)) == 1:
                    out.append(acol[0])
                else:
                    name = self._dim_name(acol, usados)
                    out.append("{" + name + "}")
                    dims.append({"name": name, "kind": "code", "segment_index": i,
                                 "in_filename": True, "sample_values": sorted(set(acol))[:20]})
            template_segs.append("".join(out))
        return f"{scheme}://{netloc}/" + "/".join(template_segs), dims

    @staticmethod
    def _nombre(netloc: str, path_template: str) -> str:
        """Nombre legible y único por productor: último segmento constante + host."""
        segs = urlparse(path_template).path.split("/")
        consts = [s for s in segs[:-1] if s and not s.startswith("{")]
        cola = consts[-1] if consts else ""
        return f"{cola} ({netloc})" if cola else netloc

    def _child_params(self, netloc: str) -> Dict[str, str]:
        """Params del hijo extractor: hereda la cortesía e inner_format del padre.
        El `entry` del padre solo vale para el productor PRIMARIO (mismo host que
        el feed de servicio); los federados traen un único GML con otro nombre →
        `*.gml` (inequívoco)."""
        base: Dict[str, str] = {}
        for k in ("inner_format", "timeout", "batch_size", "rate_limit_per_second",
                  "request_delay_ms", "max_per_hour", "file_delay", "headers", "format"):
            v = self.params.get(k)
            if v not in (None, ""):
                base[k] = str(v)
        feed_host = urlparse(self.params.get("url") or "").netloc
        parent_entry = (self.params.get("entry") or "").strip()
        base["entry"] = parent_entry if (netloc == feed_host and parent_entry) else "*.gml"
        return base

    # ── STREAM (recurso hijo promovido): extrae+parsea cada fichero ──────────────
    def _template_regex(self, template: str) -> re.Pattern:
        rx, last = "", 0
        for m in _PLACEHOLDER_RE.finditer(template):
            rx += re.escape(template[last:m.start()]) + rf"(?P<{m.group(1)}>[^/]+?)"
            last = m.end()
        rx += re.escape(template[last:])
        return re.compile("^" + rx + "$")

    def _dim_values(self, url: str, dimensions: List[Dict[str, Any]]) -> Dict[str, str]:
        template = self.params.get("_path_template")
        if not template:
            return {}
        try:
            m = self._template_regex(str(template)).match(url)
        except re.error:
            return {}
        if not m:
            return {}
        nombres = {d.get("name") for d in (dimensions or []) if d.get("name")}
        return {k: v for k, v in m.groupdict().items()
                if v is not None and (not nombres or k in nombres)}

    def _container_fmt(self, url: str) -> str:
        fmt = (self.params.get("format") or "").lower().strip()
        if fmt:
            return fmt
        for ext in ("tar.gz", "tar.bz2", "tar", "zip", "gz", "7z"):
            if url.lower().endswith(f".{ext}") or f".{ext}?" in url.lower():
                return ext
        return _ext(url)

    def _extraer(self, content: bytes, fmt: str, entry: str):
        """Reusa la extracción de Compressed File (sin duplicar lógica)."""
        if fmt == "zip":
            return _extract_zip(content, entry)
        if fmt == "gz":
            return _extract_gz(content)
        if fmt == "7z":
            return _extract_7z(content, entry)
        if fmt in _TAR_MODES:
            return _extract_tar(content, _TAR_MODES[fmt], entry)
        raise ValueError(f"Formato contenedor '{fmt}' no soportado (zip|gz|7z|tar|tar.gz|tar.bz2).")

    def stream(self) -> Generator[List[Dict[str, Any]], None, None]:
        matched_urls = self.params.get("_matched_urls")
        if not matched_urls:
            preview = self.params.get("_preview_limit")
            if preview:   # cata sobre la madre (botón Test): descubre y extrae unos pocos
                matched_urls = [h["url"] for h in self.discover(max_files=int(preview))][:int(preview)]
            if not matched_urls:
                raise RuntimeError(
                    "AtomCrawlerFetcher.stream() requiere `_matched_urls` (inyectado por el "
                    "FetcherManager para hijos promovidos). Para descubrir, ejecuta la madre con Run.")

        dimensions = self.params.get("_dimensions") or []
        entry = (self.params.get("entry") or "").strip()           # p. ej. *.cadastralparcel.gml
        inner_fmt = (self.params.get("inner_format") or "").lower().strip()
        timeout = int(self.params.get("timeout", 120))
        batch_size = int(self.params.get("batch_size", 1000) or 1000)
        file_delay = float(self.params.get("file_delay", 0) or 0)
        http_headers = self.params.get("headers", {})
        if isinstance(http_headers, str):
            http_headers = json.loads(http_headers) if http_headers.strip() else {}
        preview_limit = self.params.get("_preview_limit")
        try:
            preview_limit = int(preview_limit) if preview_limit else None
        except (TypeError, ValueError):
            preview_limit = None

        buffer: List[Dict[str, Any]] = []
        producidas = 0
        for i, url in enumerate(matched_urls):
            dims = self._dim_values(url, dimensions)
            try:
                resp = self._request(None, "GET", url, headers=http_headers, timeout=timeout)
                resp.raise_for_status()
                fmt = self._container_fmt(url)
                raw, used_entry = self._extraer(resp.content, fmt, entry)
                ifmt = inner_fmt or infer_file_format(used_entry) or ""
                if not ifmt:
                    raise ValueError(f"No se pudo inferir inner_format de '{used_entry or url}'.")
                registros = parse_structured_file(raw, ifmt, self.params, source_name=used_entry or url)
            except Exception as exc:
                # Un municipio caído/corrupto no debe tumbar toda la serie: se omite.
                logger.warning("[atom-crawler] error con %s: %s — se omite", url, exc)
                self.current_state = {"files_done": i + 1, "files_total": len(matched_urls), "last_url": url}
                continue

            for rec in registros:
                rec.update(dims)                       # etiqueta con municipio (y demás dimensiones)
                rec["_source_file_url"] = url
                buffer.append(rec)
                while len(buffer) >= batch_size:
                    yield buffer[:batch_size]
                    producidas += batch_size
                    buffer = buffer[batch_size:]

            self.current_state = {"files_done": i + 1, "files_total": len(matched_urls), "last_url": url}
            if preview_limit is not None and producidas + len(buffer) >= preview_limit:
                break
            if file_delay > 0:
                time.sleep(file_delay)

        if buffer:
            yield buffer

    # ── Extracción estándar (drena stream) ──────────────────────────────────────
    def fetch(self) -> RawData:
        records: List[Dict[str, Any]] = []
        for chunk in self.stream():
            records.extend(chunk)
        return records

    def parse(self, raw: RawData) -> ParsedData:
        return raw

    def normalize(self, parsed: ParsedData) -> DomainData:
        return parsed
