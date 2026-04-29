"""
WebTreeFetcher — único fetcher para portales web clásicos (HTML con árbol de
páginas y enlaces a XLSX/PDF/CSV/...).

Dos modos de operación, deducidos por el FetcherManager según
`resource.parent_resource_id`:

- `discover` (recurso padre): recorre el árbol BFS sin descargar ficheros,
  emite la lista de URLs hoja con metadatos. Output puro — sin BD, sin red más
  allá de las páginas HTML. El FetcherManager pasa el resultado a
  `app.services.grouping.infer()` y persiste cada propuesta como
  `ResourceCandidate`.

- `stream` (recurso hijo, auto-generado al promover una candidata): descarga
  cada URL en `_matched_urls` (inyectada por el FetcherManager desde la fila
  `ResourceCandidate` asociada) y enriquece cada registro con las
  `_dimensions` detectadas (year, month, etc.) como columnas adicionales.

FetcherParam visible al operador: SOLO `root_url`. Todo lo demás vive como
defaults internos en `_DEFAULTS`.
"""

from __future__ import annotations

import logging
import re
import time
from collections import deque, defaultdict
from pathlib import Path
from typing import Any, Dict, Generator, List, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from app.fetchers.base import BaseFetcher, DomainData, ParsedData, RawData
from app.fetchers.file_parsers import infer_file_format, parse_structured_file


logger = logging.getLogger(__name__)


_DEFAULTS: Dict[str, Any] = {
    "max_depth": 10,
    "allowed_extensions": ["pdf", "xlsx", "xls", "csv", "tsv"],
    "same_domain_only": True,
    "page_delay": 0.5,
    "file_delay": 0.0,
    "crawl_timeout": 20,
    "download_timeout": 60,
    "max_file_mb": 50,
    "navigation_link_selector": "a[href]",
    "file_link_selector": "a[href]",
    "batch_size": 500,
}

_FILENAME_YEAR_RE = re.compile(r"(?<![0-9])(?:19|20)\d{2}(?![0-9])")


def _build_profile_stats(leaves: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Genera un histograma ligero de las URLs hoja descubiertas.

    Devuelve un dict JSON-serializable con:
      - segments: frecuencia de cada token por nivel de path (level_0, level_1, ...)
      - file_extensions: conteo por extensión
      - depth_distribution: conteo por profundidad de crawling
      - total_files: número total de ficheros hoja

    Es una función pura: no toca BD ni red.
    """
    segments: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    extensions: Dict[str, int] = defaultdict(int)
    depths: Dict[str, int] = defaultdict(int)

    for leaf in leaves:
        url = leaf.get("url", "")
        depth = leaf.get("depth", 0)
        ext = leaf.get("file_type") or ""

        # Extensión
        if ext:
            extensions[ext.lower()] += 1

        # Profundidad
        depths[str(depth)] += 1

        # Segmentos de path (excluimos el último = nombre de fichero)
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split("/") if p]
        for i, part in enumerate(path_parts[:-1]):  # excluir filename
            level_key = f"level_{i}"
            segments[level_key][part] += 1

    # Calcular el nivel dominante de profundidad
    dominant_depth = None
    if depths:
        dominant_depth = max(depths.items(), key=lambda x: x[1])[0]

    # Top 10 por nivel de segmento
    top_segments = {
        level: dict(sorted(counts.items(), key=lambda x: -x[1])[:10])
        for level, counts in segments.items()
    }

    return {
        "total_files": len(leaves),
        "file_extensions": dict(sorted(extensions.items(), key=lambda x: -x[1])),
        "depth_distribution": dict(sorted(depths.items(), key=lambda x: int(x[0]))),
        "dominant_depth": dominant_depth,
        "segments": top_segments,
    }


class WebTreeFetcher(BaseFetcher):
    """Crawler de portales web. Modos: `discover` (padre) y `stream` (hijo)."""

    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        self.session = requests.Session()
        self._headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.8",
        }
        # Expuesto tras discover() para que el FetcherManager lo persista
        self.profile_stats: Dict[str, Any] = {}

    # ───────────────────────────────────────────────────────────────────
    # Helpers
    # ───────────────────────────────────────────────────────────────────

    def _opt(self, key: str) -> Any:
        if key in self.params and self.params[key] not in (None, ""):
            return self.params[key]
        return _DEFAULTS.get(key)

    def _root_url(self) -> str:
        url = self.params.get("root_url") or self.params.get("url") or self.params.get("start_url")
        if not url:
            raise ValueError("WebTreeFetcher requiere el parámetro `root_url`")
        return url

    def _allowed_extensions(self) -> set:
        raw = self._opt("allowed_extensions")
        if isinstance(raw, str):
            stripped = raw.strip()
            if stripped.startswith("["):
                import json
                raw = json.loads(stripped)
            else:
                raw = [e.strip() for e in stripped.split(",") if e.strip()]
        return {str(ext).lower().lstrip(".") for ext in raw}

    def _resolve_format(self, url: str) -> str:
        return infer_file_format(url) or ""

    def _file_allowed(self, url: str, allowed: set) -> bool:
        fmt = self._resolve_format(url)
        return bool(fmt and fmt in allowed)

    def _page_allowed(self, url: str, root_netloc: str, same_domain_only: bool) -> bool:
        if same_domain_only:
            netloc = urlparse(url).netloc
            if netloc and netloc != root_netloc:
                return False
        return True

    def _bool(self, value: Any, default: bool) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "si", "on"}

    def _extract_links(self, soup: BeautifulSoup, base_url: str, selector: str) -> List[Tuple[str, str]]:
        links: List[Tuple[str, str]] = []
        for el in soup.select(selector):
            href = el.get("href")
            if not href:
                continue
            absolute = urljoin(base_url, href)
            anchor = " ".join(el.get_text(" ", strip=True).split())
            links.append((absolute, anchor))
        return links

    # ───────────────────────────────────────────────────────────────────
    # DISCOVER mode (padre)
    # ───────────────────────────────────────────────────────────────────

    def discover(self) -> List[Dict[str, Any]]:
        """
        Recorre el árbol BFS y devuelve la lista de URLs hoja (ficheros).
        También calcula y almacena `self.profile_stats` con el histograma
        de segmentos, extensiones y profundidad.
        No descarga ficheros. No toca BD.
        """
        root_url = self._root_url()
        max_depth = int(self._opt("max_depth"))
        page_delay = float(self._opt("page_delay"))
        crawl_timeout = int(self._opt("crawl_timeout"))
        same_domain_only = self._bool(self._opt("same_domain_only"), True)
        allowed_ext = self._allowed_extensions()
        nav_selector = str(self._opt("navigation_link_selector"))
        file_selector = str(self._opt("file_link_selector"))

        root_netloc = urlparse(root_url).netloc
        queue: deque = deque([(root_url, 0)])
        visited_pages: set = set()
        visited_files: set = set()
        leaves: List[Dict[str, Any]] = []

        while queue:
            page_url, depth = queue.popleft()
            if page_url in visited_pages:
                continue
            if depth > max_depth:
                continue
            if not self._page_allowed(page_url, root_netloc, same_domain_only):
                continue

            visited_pages.add(page_url)
            logger.info("[WebTree.discover] depth=%s %s", depth, page_url)

            try:
                response = self._request(
                    self.session, "GET", page_url,
                    headers=self._headers, timeout=crawl_timeout,
                )
            except Exception as exc:
                logger.warning("[WebTree.discover] error en %s: %s", page_url, exc)
                continue

            content_type = (response.headers.get("Content-Type") or "").lower()
            if "html" not in content_type and "xml" not in content_type:
                continue

            soup = BeautifulSoup(response.text, "html.parser")

            for file_url, anchor in self._extract_links(soup, page_url, file_selector):
                if file_url in visited_files:
                    continue
                if not self._file_allowed(file_url, allowed_ext):
                    continue
                visited_files.add(file_url)
                leaves.append({
                    "url": file_url,
                    "file_type": self._resolve_format(file_url),
                    "source_page": page_url,
                    "depth": depth,
                    "anchor_text": anchor,
                })

            if depth < max_depth:
                for next_url, _ in self._extract_links(soup, page_url, nav_selector):
                    if next_url in visited_pages:
                        continue
                    if not self._page_allowed(next_url, root_netloc, same_domain_only):
                        continue
                    queue.append((next_url, depth + 1))

            self.current_state = {
                "last_page_url": page_url,
                "last_depth": depth,
                "pages_seen": len(visited_pages),
                "files_seen": len(visited_files),
            }

            if page_delay > 0:
                time.sleep(page_delay)

        # Calcular y almacenar histograma (función pura)
        self.profile_stats = _build_profile_stats(leaves)
        logger.info(
            "[WebTree.discover] %s ficheros hoja en %s páginas | stats: %s ext, depth dominante %s",
            len(leaves), len(visited_pages),
            list(self.profile_stats.get("file_extensions", {}).keys()),
            self.profile_stats.get("dominant_depth"),
        )
        return leaves

    # ───────────────────────────────────────────────────────────────────
    # STREAM mode (hijo promovido)
    # ───────────────────────────────────────────────────────────────────

    def _extract_dim_values(self, url: str, dimensions: List[Dict[str, Any]]) -> Dict[str, str]:
        parsed = urlparse(url)
        segs = [s for s in parsed.path.split("/") if s]
        if not segs:
            return {}
        path_segs = segs[:-1]
        filename = segs[-1]
        out: Dict[str, str] = {}
        for d in dimensions or []:
            name = d.get("name")
            if not name:
                continue
            if d.get("in_filename"):
                m = _FILENAME_YEAR_RE.search(filename)
                if m:
                    out[name] = m.group(0)
                continue
            idx = d.get("segment_index")
            if isinstance(idx, int) and 0 <= idx < len(path_segs):
                out[name] = path_segs[idx]
        return out

    def _download_and_parse(self, url: str) -> List[Dict[str, Any]]:
        timeout = int(self._opt("download_timeout"))
        max_mb = int(self._opt("max_file_mb"))
        response = self._request(
            self.session, "GET", url,
            headers=self._headers, timeout=timeout, stream=True,
        )
        chunks = []
        received = 0
        for chunk in response.iter_content(chunk_size=65536):
            if not chunk:
                continue
            chunks.append(chunk)
            received += len(chunk)
            if received > max_mb * 1024 * 1024:
                raise RuntimeError(f"Fichero demasiado grande (>{max_mb} MB): {url}")
        content = b"".join(chunks)
        fmt = self._resolve_format(url)
        return parse_structured_file(content, fmt, {}, source_name=url)

    def stream(self) -> Generator[List[Dict[str, Any]], None, None]:
        matched_urls = self.params.get("_matched_urls")
        if not matched_urls:
            raise RuntimeError(
                "WebTreeFetcher.stream() requiere `_matched_urls` (inyectado por el "
                "FetcherManager para Resources hijos promovidos desde una candidata)."
            )
        dimensions = self.params.get("_dimensions") or []
        batch_size = int(self._opt("batch_size"))
        file_delay = float(self._opt("file_delay"))

        buffer: List[Dict[str, Any]] = []
        for i, url in enumerate(matched_urls):
            try:
                records = self._download_and_parse(url)
            except Exception as exc:
                logger.warning("[WebTree.stream] error descargando %s: %s", url, exc)
                continue

            dim_values = self._extract_dim_values(url, dimensions)
            metadata = {
                **dim_values,
                "_source_file_url": url,
                "_source_file_name": Path(urlparse(url).path).name,
                "_source_format": self._resolve_format(url),
            }
            for record in records:
                record.update(metadata)
            buffer.extend(records)

            self.current_state = {
                "files_done": i + 1,
                "files_total": len(matched_urls),
                "last_url": url,
            }

            while len(buffer) >= batch_size:
                yield buffer[:batch_size]
                buffer = buffer[batch_size:]

            if file_delay > 0:
                time.sleep(file_delay)

        if buffer:
            yield buffer

    # ───────────────────────────────────────────────────────────────────
    # BaseFetcher contract
    # ───────────────────────────────────────────────────────────────────

    def fetch(self) -> RawData:
        records: List[Dict[str, Any]] = []
        for chunk in self.stream():
            records.extend(chunk)
        return records

    def parse(self, raw: RawData) -> ParsedData:
        return raw

    def normalize(self, parsed: ParsedData) -> DomainData:
        return parsed
