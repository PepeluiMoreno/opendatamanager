"""
PortalFilesCataloguer — meta-fetcher que recorre un portal web y produce un
catálogo de ficheros descargables, clasificados a partir del análisis del path
de cada URL en un section_id jerárquico más atributos (ejercicio, trimestre…).

Emite una fila por cada fichero descubierto. La tabla resultante es el contrato
entre este fetcher y los PortalFileDataFetcher posteriores, que filtran por
section_id y procesan los ficheros de su sección.
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections import deque
from typing import Any, Dict, Generator, Iterable, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from app.fetchers.base import BaseFetcher, DomainData, ParsedData, RawData
from app.fetchers.file_parsers import infer_file_format

logger = logging.getLogger(__name__)


def _parse_json_param(value: Any, default: Any) -> Any:
    if value in (None, ""):
        return default
    if isinstance(value, str):
        return json.loads(value)
    return value


def _bool_param(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "si", "on"}


DEFAULT_ATTRIBUTE_PATTERNS = {
    "ejercicio": r"^(19|20)\d{2}$",
    "trimestre": r"^([1-4])o?T$",
}


class PortalFilesCataloguer(BaseFetcher):
    def __init__(self, params: Dict[str, str]):
        super().__init__(params)
        self.session = requests.Session()
        self._headers = self._build_headers()
        self._segment_prefix_pattern = re.compile(
            self.params.get("segment_prefix_strip_pattern") or r"^[a-z]\d*-"
        )
        self._path_prefix_strip = self.params.get("path_prefix_strip") or ""
        self._noise_segments = set(
            _parse_json_param(self.params.get("noise_segments"), [])
        )
        self._attribute_patterns = {
            name: re.compile(pat)
            for name, pat in _parse_json_param(
                self.params.get("attribute_patterns"),
                DEFAULT_ATTRIBUTE_PATTERNS,
            ).items()
        }
        self._filename_attribute_patterns = {
            name: re.compile(pat)
            for name, pat in _parse_json_param(
                self.params.get("filename_attribute_patterns"),
                {},
            ).items()
        }
        self._allowed_extensions = {
            e.lower().lstrip(".")
            for e in _parse_json_param(
                self.params.get("allowed_extensions"),
                ["pdf", "xlsx", "xls", "csv", "tsv"],
            )
        }

    def _build_headers(self) -> Dict[str, str]:
        defaults = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.8",
        }
        extra = _parse_json_param(self.params.get("headers"), {})
        return {**defaults, **extra}

    def _start_urls(self) -> List[str]:
        explicit = _parse_json_param(self.params.get("start_urls"), [])
        if explicit:
            return [str(u) for u in explicit]
        one = self.params.get("start_url") or self.params.get("url")
        if not one:
            raise ValueError("PortalFilesCataloguer requiere 'start_url' o 'start_urls'")
        return [one]

    def _match_any(self, url: str, patterns: Iterable[str]) -> bool:
        return any(p and p in url for p in patterns)

    def _page_allowed(self, url: str, root_netloc: str) -> bool:
        include = _parse_json_param(self.params.get("page_include_patterns"), [])
        exclude = _parse_json_param(self.params.get("page_exclude_patterns"), [])
        same_domain_only = _bool_param(self.params.get("same_domain_only"), True)
        if same_domain_only and urlparse(url).netloc and urlparse(url).netloc != root_netloc:
            return False
        if include and url not in self._start_urls() and not self._match_any(url, include):
            return False
        if exclude and self._match_any(url, exclude):
            return False
        return True

    def _file_allowed(self, url: str) -> bool:
        fmt = infer_file_format(url)
        if not fmt or fmt not in self._allowed_extensions:
            return False
        include = _parse_json_param(self.params.get("file_include_patterns"), [])
        exclude = _parse_json_param(self.params.get("file_exclude_patterns"), [])
        if include and not self._match_any(url, include):
            return False
        if exclude and self._match_any(url, exclude):
            return False
        return True

    def _classify(self, file_url: str, anchor_text: str, page_url: str) -> Optional[Dict[str, Any]]:
        """Analyse the file URL path and produce a catalog record."""
        path = urlparse(file_url).path

        if self._path_prefix_strip and path.startswith(self._path_prefix_strip):
            path_body = path[len(self._path_prefix_strip):]
        else:
            path_body = path

        segments = [s for s in path_body.split("/") if s]
        if not segments:
            return None

        filename = segments[-1]
        body_segments = segments[:-1]

        section_parts: List[str] = []
        attributes: Dict[str, str] = {}

        for seg in body_segments:
            if seg in self._noise_segments:
                continue
            matched_attr = False
            for attr_name, pattern in self._attribute_patterns.items():
                m = pattern.match(seg)
                if m:
                    attributes[attr_name] = m.group(1) if m.groups() else seg
                    matched_attr = True
                    break
            if matched_attr:
                continue
            clean = self._segment_prefix_pattern.sub("", seg)
            section_parts.append(clean)

        for attr_name, pattern in self._filename_attribute_patterns.items():
            m = pattern.search(filename)
            if m:
                attributes[attr_name] = m.group(1) if m.groups() else m.group(0)

        fmt = infer_file_format(file_url)

        record = {
            "section_id": ".".join(section_parts) if section_parts else "root",
            "section_path": list(section_parts),
            "url": file_url,
            "format": fmt,
            "filename": filename,
            "anchor_text": anchor_text or "",
            "page_url": page_url,
        }
        record.update(attributes)
        return record

    def stream(self) -> Generator[List[Dict[str, Any]], None, None]:
        start_urls = self._start_urls()
        max_depth = int(self.params.get("max_depth", 10))
        batch_size = int(self.params.get("batch_size", 500))
        page_delay = float(self.params.get("page_delay", 0))
        crawl_timeout = int(self.params.get("crawl_timeout", 15))
        navigation_attr = self.params.get("navigation_link_attr", "href")
        file_attr = self.params.get("file_link_attr", "href")
        navigation_selector = self.params.get("navigation_link_selector") or "a[href]"
        file_selector = self.params.get("file_link_selector") or "a[href]"

        root_netloc = urlparse(start_urls[0]).netloc
        queue: deque = deque((url, 0) for url in start_urls)
        visited_pages: set = set()
        seen_files: set = set()
        buffer: List[Dict[str, Any]] = []

        while queue:
            page_url, depth = queue.popleft()
            if page_url in visited_pages or depth > max_depth:
                continue
            if not self._page_allowed(page_url, root_netloc):
                continue

            visited_pages.add(page_url)
            logger.info("[PortalFilesCataloguer] depth=%s %s", depth, page_url)

            try:
                response = self._request(
                    self.session, "GET", page_url,
                    headers=self._headers, timeout=crawl_timeout,
                )
            except Exception as exc:
                logger.warning("[PortalFilesCataloguer] skip %s: %s", page_url, exc)
                continue

            soup = BeautifulSoup(response.text, "html.parser")

            for el in soup.select(file_selector):
                href = el.get(file_attr)
                if not href:
                    continue
                file_url = urljoin(page_url, href)
                if file_url in seen_files or not self._file_allowed(file_url):
                    continue
                seen_files.add(file_url)
                anchor = " ".join(el.get_text(" ", strip=True).split())
                entry = self._classify(file_url, anchor, page_url)
                if entry:
                    buffer.append(entry)
                    while len(buffer) >= batch_size:
                        yield buffer[:batch_size]
                        buffer = buffer[batch_size:]

            if depth < max_depth:
                for el in soup.select(navigation_selector):
                    href = el.get(navigation_attr)
                    if not href:
                        continue
                    next_url = urljoin(page_url, href)
                    if next_url in visited_pages:
                        continue
                    if not self._page_allowed(next_url, root_netloc):
                        continue
                    queue.append((next_url, depth + 1))

            self.current_state = {
                "last_page_url": page_url,
                "last_depth": depth,
                "pages_seen": len(visited_pages),
                "files_cataloged": len(seen_files),
            }

            if page_delay > 0:
                time.sleep(page_delay)

        if buffer:
            yield buffer

    def fetch(self) -> RawData:
        records = []
        for chunk in self.stream():
            records.extend(chunk)
        return records

    def parse(self, raw: RawData) -> ParsedData:
        return raw

    def normalize(self, parsed: ParsedData) -> DomainData:
        return parsed
