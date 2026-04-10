"""
UrlLoopHtmlFetcher — HTML scraper con pivot sobre lista de URLs y paginación interna.

Patrón de uso:
  1. Se genera una URL por cada valor del pivot: url_template.format(value=v, page=N)
  2. En cada página se extraen N registros usando selectores CSS sobre atributos data-*,
     texto de elementos o atributos href.
  3. Se avanza a la página siguiente detectando un enlace con un selector CSS dado
     (típicamente rel="next") hasta que desaparece o se alcanza max_pages.

Parámetros obligatorios:
    url_template    — plantilla de URL con {value} y opcionalmente {page}
                      Ej: "https://example.com/search/{value}/l?pagina={page}"
    pivot_values    — JSON array de valores sobre los que pivotar
                      Ej: '["madrid","barcelona","sevilla"]'
    record_selector — selector CSS del elemento raíz de cada registro
                      Ej: "article[data-agency-id]"

Extracción de campos (al menos uno obligatorio):
    field_attrs     — JSON: {"campo": "nombre-del-atributo-html"}
                      Extrae el valor de ese atributo del elemento raíz.
                      Ej: '{"agency_id": "data-agency-id", "nombre": "data-agency-name"}'
    field_selectors — JSON: {"campo": "selector-css"}
                      Extrae el texto del primer subelemento que coincida.
                      Ej: '{"titulo": "h3.title", "precio": ".price"}'
    field_attr_selectors — JSON: {"campo": {"selector": "css", "attr": "atributo"}}
                      Extrae el atributo de un subelemento específico.
                      Ej: '{"url": {"selector": "a.link", "attr": "href"}}'
    field_all_text  — JSON: {"campo": "selector-css"}
                      Concatena el texto de TODOS los subelementos que coincidan.

Paginación:
    next_page_selector — selector CSS del enlace a la página siguiente
                         Ej: 'a[rel="next"]'  (default: vacío = sin paginación)
    next_page_attr     — atributo del enlace de paginación (default: "href")
    page_base_url      — prefijo para hrefs relativos (default: origen de url_template)

Comportamiento:
    pivot_field        — nombre del campo que almacena el valor del pivot actual
                         (default: "pivot_value")
    delay_between_pages   — segundos entre páginas (default: 1.5)
    delay_between_pivots  — segundos entre valores del pivot (default: 2.0)
    max_pages             — máximo de páginas por pivot (default: 500)
    stop_on_error         — si True, para al primer error de un pivot (default: False)
    timeout               — timeout HTTP (default: 30)

Resume:
    Soporta resume via _resume_state: {"pivot_index": N, "page_num": M}
"""

import html as html_lib
import json
import logging
import re
import time
from typing import Any, Dict, Generator, List, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from app.fetchers.base import BaseFetcher, RawData, ParsedData, DomainData

logger = logging.getLogger(__name__)


def _parse_json(value: Any) -> Any:
    if isinstance(value, str):
        s = value.strip()
        return json.loads(s) if s else {}
    return value or {}


def _unescape(text: str) -> str:
    return html_lib.unescape(text or "").strip()


class UrlLoopHtmlFetcher(BaseFetcher):
    """
    Fetcher genérico para páginas HTML con:
      - Pivot sobre una lista de valores (uno por URL)
      - Paginación interna por página
      - Extracción de registros múltiples por página via selectores CSS / atributos HTML
    """

    _DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9",
    }

    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        extra_headers = _parse_json(params.get("headers", {}))
        self.session = requests.Session()
        self.session.headers.update({**self._DEFAULT_HEADERS, **extra_headers})

    # ------------------------------------------------------------------
    # Helpers de configuración
    # ------------------------------------------------------------------

    def _get_pivot_values(self) -> List[str]:
        raw = self.params.get("pivot_values", "")
        if not raw:
            raise ValueError("El parámetro 'pivot_values' es obligatorio")
        if isinstance(raw, str):
            s = raw.strip()
            return json.loads(s) if s.startswith("[") else [v.strip() for v in s.split(",") if v.strip()]
        return list(raw)

    def _build_url(self, template: str, value: str, page: int) -> str:
        return template.replace("{value}", value).replace("{page}", str(page))

    def _page_base(self) -> str:
        tmpl = self.params.get("url_template", "")
        p = urlparse(tmpl.replace("{value}", "x").replace("{page}", "1"))
        return f"{p.scheme}://{p.netloc}"

    # ------------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------------

    def _fetch(self, url: str) -> BeautifulSoup:
        resp = self._request(
            self.session, "GET", url,
            timeout=int(self.params.get("timeout", 30)),
        )
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")

    # ------------------------------------------------------------------
    # Extracción de un registro
    # ------------------------------------------------------------------

    def _extract_record(self, el: BeautifulSoup, pivot_value: str) -> Dict[str, Any]:
        """
        Extrae todos los campos configurados de un elemento raíz.
        """
        record: Dict[str, Any] = {}

        # 1. Atributos del elemento raíz: {"campo": "nombre-attr"}
        for field, attr in _parse_json(self.params.get("field_attrs", {})).items():
            val = el.get(attr)
            record[field] = _unescape(val) if isinstance(val, str) else val

        # 2. Texto de subelementos: {"campo": "selector"}
        for field, selector in _parse_json(self.params.get("field_selectors", {})).items():
            sub = el.select_one(selector)
            record[field] = _unescape(sub.get_text()) if sub else None

        # 3. Atributo de subelemento: {"campo": {"selector": "...", "attr": "..."}}
        for field, cfg in _parse_json(self.params.get("field_attr_selectors", {})).items():
            sub = el.select_one(cfg.get("selector", ""))
            record[field] = sub.get(cfg.get("attr", "href")) if sub else None

        # 4. Texto de todos los subelementos: {"campo": "selector"} → concatenado
        sep = self.params.get("field_all_separator", " | ")
        for field, selector in _parse_json(self.params.get("field_all_text", {})).items():
            subs = el.select(selector)
            record[field] = sep.join(_unescape(s.get_text()) for s in subs) if subs else None

        # 5. Valor del pivot
        pivot_field = self.params.get("pivot_field", "pivot_value")
        record[pivot_field] = pivot_value

        return record

    # ------------------------------------------------------------------
    # Paginación
    # ------------------------------------------------------------------

    def _next_page_url(self, soup: BeautifulSoup) -> Optional[str]:
        selector = self.params.get("next_page_selector", "")
        if not selector:
            return None
        link = soup.select_one(selector)
        if not link:
            return None
        attr = self.params.get("next_page_attr", "href")
        href = link.get(attr)
        if not href:
            return None
        return (self._page_base() + href) if href.startswith("/") else href

    # ------------------------------------------------------------------
    # Interfaz BaseFetcher
    # ------------------------------------------------------------------

    def stream(self) -> Generator[List[Dict], None, None]:
        url_template    = self.params.get("url_template", "")
        record_selector = self.params.get("record_selector", "")
        if not url_template or not record_selector:
            raise ValueError("Parámetros obligatorios: 'url_template' y 'record_selector'")

        pivot_values    = self._get_pivot_values()
        delay_pages     = float(self.params.get("delay_between_pages", 1.5))
        delay_pivots    = float(self.params.get("delay_between_pivots", 2.0))
        max_pages       = int(self.params.get("max_pages", 500))
        stop_on_error   = str(self.params.get("stop_on_error", "false")).lower() == "true"
        preview_limit   = int(self.params.get("_preview_limit", 0))
        total_yielded   = 0

        resume      = self.params.get("_resume_state", {})
        start_pivot = resume.get("pivot_index", 0)

        for pivot_idx, pivot_value in enumerate(pivot_values):
            if pivot_idx < start_pivot:
                continue

            page_num = 1
            if pivot_idx == start_pivot:
                page_num = resume.get("page_num", 1)

            url = self._build_url(url_template, pivot_value, page_num)
            logger.info(f"[{pivot_idx+1}/{len(pivot_values)}] pivot={pivot_value!r} pág={page_num}")

            while page_num <= max_pages:
                try:
                    soup = self._fetch(url)
                except Exception as exc:
                    logger.error(f"  Error fetching {url}: {exc}")
                    if stop_on_error:
                        raise
                    break

                elements = soup.select(record_selector)
                records = [self._extract_record(el, pivot_value) for el in elements]
                logger.info(f"  pág. {page_num}: {len(records)} registros")

                if not records:
                    break

                if preview_limit:
                    records = records[: preview_limit - total_yielded]

                if records:
                    yield records
                    total_yielded += len(records)

                self.current_state = {"pivot_index": pivot_idx, "page_num": page_num}

                if preview_limit and total_yielded >= preview_limit:
                    return

                next_url = self._next_page_url(soup)
                if not next_url:
                    break

                url      = next_url
                page_num += 1
                if delay_pages > 0:
                    time.sleep(delay_pages)

            if delay_pivots > 0 and pivot_idx < len(pivot_values) - 1:
                time.sleep(delay_pivots)

    def fetch(self) -> RawData:
        all_records: List[Dict] = []
        for chunk in self.stream():
            all_records.extend(chunk)
        logger.info(f"UrlLoopHtml: {len(all_records)} registros totales")
        return all_records

    def parse(self, raw: RawData) -> ParsedData:
        return raw

    def normalize(self, parsed: ParsedData) -> DomainData:
        return parsed
