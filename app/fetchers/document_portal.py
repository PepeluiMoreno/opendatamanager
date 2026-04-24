"""
DocumentPortalFetcher — crawler genérico para portales documentales.

Recorre un árbol de páginas HTML, descubre enlaces a ficheros descargables y
parsea cada artefacto según su extensión mediante los parsers compartidos.
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections import deque
from pathlib import Path
from typing import Any, Dict, Generator, Iterable, List, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from app.fetchers.base import BaseFetcher, DomainData, ParsedData, RawData
from app.fetchers.file_parsers import infer_file_format, parse_structured_file

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


class DocumentPortalFetcher(BaseFetcher):
    def __init__(self, params: Dict[str, str]):
        super().__init__(params)
        self.session = requests.Session()
        self._headers = self._build_headers()
        self._parser_options = _parse_json_param(self.params.get("parser_options"), {})
        self._format_overrides = _parse_json_param(self.params.get("format_overrides"), {})
        self._context_selectors = _parse_json_param(self.params.get("page_context_selectors"), {})
        self._context_attr_selectors = _parse_json_param(
            self.params.get("page_context_attr_selectors"),
            {},
        )
        self._context_url_patterns = _parse_json_param(
            self.params.get("page_context_url_patterns"),
            {},
        )
        self._context_url_overrides = _parse_json_param(
            self.params.get("page_context_url_overrides"),
            {},
        )
        self._allowed_extensions = {
            ext.lower().lstrip(".")
            for ext in _parse_json_param(
                self.params.get("allowed_extensions"),
                ["pdf", "xlsx", "xls", "csv", "tsv"],
            )
        }

    def _build_headers(self) -> Dict[str, str]:
        extra = _parse_json_param(self.params.get("headers"), {})
        defaults = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.8",
        }
        return {**defaults, **extra}

    def _start_urls(self) -> List[str]:
        explicit = _parse_json_param(self.params.get("start_urls"), [])
        if explicit:
            return [str(url) for url in explicit]
        start_url = self.params.get("start_url") or self.params.get("url")
        if not start_url:
            raise ValueError("DocumentPortalFetcher requiere 'start_url' o 'start_urls'")
        return [start_url]

    def _extract_context(self, soup: BeautifulSoup, page_url: str, depth: int, inherited: Dict[str, Any]) -> Dict[str, Any]:
        context = dict(inherited)
        for field, selector in self._context_selectors.items():
            element = soup.select_one(selector)
            context[field] = " ".join(element.get_text(" ", strip=True).split()) if element else None

        for field, cfg in self._context_attr_selectors.items():
            selector = cfg.get("selector", "")
            attr = cfg.get("attr", "href")
            element = soup.select_one(selector)
            context[field] = element.get(attr) if element else None

        for field, pattern in self._context_url_patterns.items():
            m = re.search(pattern, page_url)
            context[field] = m.group(1) if m and m.lastindex else (m.group(0) if m else None)

        for url_pattern, field_overrides in self._context_url_overrides.items():
            if url_pattern and url_pattern in page_url:
                context.update(field_overrides)
                break

        context["_source_page_url"] = page_url
        context["_source_depth"] = depth
        return context

    def _match_any(self, url: str, patterns: Iterable[str]) -> bool:
        for pattern in patterns:
            if pattern and pattern in url:
                return True
        return False

    def _page_allowed(self, url: str, root_netloc: str) -> bool:
        include = _parse_json_param(self.params.get("page_include_patterns"), [])
        exclude = _parse_json_param(self.params.get("page_exclude_patterns"), [])
        same_domain_only = _bool_param(self.params.get("same_domain_only"), True)

        if same_domain_only and urlparse(url).netloc and urlparse(url).netloc != root_netloc:
            return False
        if include and not self._match_any(url, include):
            return False
        if exclude and self._match_any(url, exclude):
            return False
        return True

    def _file_allowed(self, url: str) -> bool:
        include = _parse_json_param(self.params.get("file_include_patterns"), [])
        exclude = _parse_json_param(self.params.get("file_exclude_patterns"), [])

        fmt = self._resolve_format(url)
        if not fmt or fmt not in self._allowed_extensions:
            return False
        if include and not self._match_any(url, include):
            return False
        if exclude and self._match_any(url, exclude):
            return False
        return True

    def _resolve_links(self, soup: BeautifulSoup, base_url: str, selector: str, attr: str) -> List[Tuple[str, str]]:
        links: List[Tuple[str, str]] = []
        for element in soup.select(selector):
            href = element.get(attr)
            if not href:
                continue
            links.append((urljoin(base_url, href), " ".join(element.get_text(" ", strip=True).split())))
        return links

    def _navigation_selector(self) -> str:
        return self.params.get("navigation_link_selector") or "a[href]"

    def _file_selector(self) -> str:
        return self.params.get("file_link_selector") or "a[href]"

    def _resolve_format(self, url: str) -> str:
        for pattern, forced_format in self._format_overrides.items():
            if pattern and pattern in url:
                return str(forced_format).lower().strip()
        return infer_file_format(url)

    def _options_for_format(self, fmt: str) -> Dict[str, Any]:
        common = _parse_json_param(self.params.get("common_parser_options"), {})
        specific = self._parser_options.get(fmt, {})
        return {**common, **specific}

    def _download_file(self, url: str, fmt: str) -> List[Dict[str, Any]]:
        timeout = int(self.params.get("timeout", 60))
        response = self._request(self.session, "GET", url, headers=self._headers, timeout=timeout)
        return parse_structured_file(response.content, fmt, self._options_for_format(fmt), source_name=url)

    def stream(self) -> Generator[List[Dict[str, Any]], None, None]:
        start_urls = self._start_urls()
        max_depth = int(self.params.get("max_depth", 0))
        batch_size = int(self.params.get("batch_size", 500))
        page_delay = float(self.params.get("page_delay", 0))
        file_delay = float(self.params.get("file_delay", 0))
        navigation_attr = self.params.get("navigation_link_attr", "href")
        file_attr = self.params.get("file_link_attr", "href")

        root_netloc = urlparse(start_urls[0]).netloc
        queue = deque((url, 0, {}) for url in start_urls)
        visited_pages = set()
        visited_files = set()
        buffer: List[Dict[str, Any]] = []

        while queue:
            page_url, depth, inherited = queue.popleft()
            if page_url in visited_pages:
                continue
            if depth > max_depth:
                continue
            if not self._page_allowed(page_url, root_netloc):
                continue

            visited_pages.add(page_url)
            logger.info("[DocumentPortalFetcher] Crawling depth=%s %s", depth, page_url)

            response = self._request(self.session, "GET", page_url, headers=self._headers)
            soup = BeautifulSoup(response.text, "html.parser")
            page_context = self._extract_context(soup, page_url, depth, inherited)

            file_links = self._resolve_links(soup, page_url, self._file_selector(), file_attr)
            for file_url, anchor_text in file_links:
                if file_url in visited_files or not self._file_allowed(file_url):
                    continue

                visited_files.add(file_url)
                fmt = self._resolve_format(file_url)
                records = self._download_file(file_url, fmt)

                metadata = {
                    **page_context,
                    "_source_file_url": file_url,
                    "_source_file_name": Path(urlparse(file_url).path).name,
                    "_source_format": fmt,
                    "_source_anchor_text": anchor_text,
                }
                for record in records:
                    record.update(metadata)

                buffer.extend(records)
                logger.info(
                    "[DocumentPortalFetcher] %s -> %s registros (%s)",
                    file_url,
                    len(records),
                    fmt,
                )

                while len(buffer) >= batch_size:
                    yield buffer[:batch_size]
                    buffer = buffer[batch_size:]

                if file_delay > 0:
                    time.sleep(file_delay)

            if depth < max_depth:
                child_context_keys = _parse_json_param(self.params.get("inherit_context_fields"), [])
                child_context = {key: page_context.get(key) for key in child_context_keys} if child_context_keys else page_context
                for next_url, _ in self._resolve_links(soup, page_url, self._navigation_selector(), navigation_attr):
                    if next_url not in visited_pages and self._page_allowed(next_url, root_netloc):
                        queue.append((next_url, depth + 1, child_context))

            self.current_state = {
                "last_page_url": page_url,
                "last_depth": depth,
                "pages_seen": len(visited_pages),
                "files_seen": len(visited_files),
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
