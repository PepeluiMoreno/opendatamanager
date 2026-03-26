"""
searchloop_html.py

SearchLoopHtmlFetcher - Fetcher para buscadores HTML que pivota sobre los valores
de un campo <select> del formulario de búsqueda.

Flujo:
  1. Carga la página del formulario
  2. Extrae las opciones del <select> indicado por `search_field_name`
     (o usa `search_field_values` si se proporcionan manualmente)
  3. Por cada valor itera: envía el formulario y recoge los resultados
  4. Soporta paginación simple por link (next_page_selector)
"""
import json
import re
import time
import logging
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from typing import Dict, Generator, List, Any, Optional

from app.fetchers.base import BaseFetcher, RawData, ParsedData, DomainData

logger = logging.getLogger(__name__)


class SearchLoopHtmlFetcher(BaseFetcher):

    def __init__(self, params):
        super().__init__(params)
        self.session = requests.Session()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_headers(self) -> Dict[str, str]:
        headers = self.params.get("headers", {})
        if isinstance(headers, str):
            headers = json.loads(headers)
        defaults = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.8",
        }
        return {**defaults, **headers}

    def _fetch(self, url: str, method: str = "GET",
               data: Optional[Dict] = None, params: Optional[Dict] = None) -> BeautifulSoup:
        timeout = int(self.params.get("timeout", 30))
        max_retries = int(self.params.get("max_retries", 3))
        retry_delay = float(self.params.get("retry_delay", 2.0))
        hdrs = self._get_headers()

        for attempt in range(max_retries + 1):
            try:
                if method.upper() == "POST":
                    resp = self.session.post(url, data=data, params=params,
                                             headers=hdrs, timeout=timeout)
                else:
                    resp = self.session.get(url, params=params,
                                            headers=hdrs, timeout=timeout)
                resp.raise_for_status()
                return BeautifulSoup(resp.text, "html.parser")
            except Exception as exc:
                if attempt == max_retries:
                    raise
                wait = retry_delay * (2 ** attempt)
                logger.warning(f"Intento {attempt + 1} fallido ({exc}), reintento en {wait}s")
                time.sleep(wait)

    # ------------------------------------------------------------------
    # Auto-discovery de valores del select
    # ------------------------------------------------------------------

    def _discover_search_values(self) -> List[str]:
        """
        Carga la página del formulario y extrae los <option value="...">
        del <select> cuyo name/id coincide con `search_field_name`.
        Excluye la opción vacía o "-- Seleccione --".
        """
        url = self.params["url"]
        field_name = self.params["search_field_name"]

        logger.info(f"Descubriendo valores del select '{field_name}' en {url}")
        soup = self._fetch(url)

        select = (
            soup.find("select", {"name": field_name}) or
            soup.find("select", {"id": field_name})
        )
        if not select:
            raise ValueError(
                f"No se encontró <select name='{field_name}'> en {url}. "
                "Revisa search_field_name."
            )

        values = [
            opt["value"]
            for opt in select.find_all("option")
            if opt.get("value", "").strip() and opt["value"].strip() not in ("", "0", "-1")
        ]
        logger.info(f"Descubiertos {len(values)} valores: {values[:5]}{'...' if len(values) > 5 else ''}")
        return values

    # ------------------------------------------------------------------
    # Extracción de tabla
    # ------------------------------------------------------------------

    def _extract_table(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        rows_selector = self.params.get("rows_selector", "table tr")
        rows = soup.select(rows_selector)
        if not rows:
            return []

        has_header = self.params.get("has_header", True)
        headers: List[str] = []
        start = 0

        if has_header:
            for selector in ("th", "td"):
                headers = [c.get_text(strip=True) for c in rows[0].select(selector)]
                if headers:
                    break
            start = 1

        if not headers:
            n_cols = len(rows[start].select("td")) if start < len(rows) else 0
            headers = [f"col_{i}" for i in range(n_cols)]

        data = []
        for row in rows[start:]:
            cells = row.select("td")
            if not cells:
                continue
            record = {}
            for i, cell in enumerate(cells):
                key = headers[i] if i < len(headers) else f"col_{i}"
                text = re.sub(r"\s+", " ", cell.get_text(strip=True))
                record[key] = text
            if record:
                data.append(record)
        return data

    # ------------------------------------------------------------------
    # Fetch por valor de búsqueda (con paginación opcional)
    # ------------------------------------------------------------------

    def _fetch_for_value(self, search_value: str) -> List[Dict[str, str]]:
        url = self.params["url"]
        method = self.params.get("method", "GET").upper()
        search_field_name = self.params["search_field_name"]
        next_selector = self.params.get("next_page_selector", "")
        max_pages = int(self.params.get("max_pages", 50))
        delay = float(self.params.get("delay_between_pages", 0.5))

        # Parámetros extra fijos
        extra = self.params.get("extra_params", {})
        if isinstance(extra, str):
            extra = json.loads(extra)

        form_data = {search_field_name: search_value, **extra}
        current_url = url
        all_records: List[Dict] = []
        page = 0

        while page < max_pages:
            if method == "POST":
                soup = self._fetch(current_url, "POST", data=form_data)
            else:
                soup = self._fetch(current_url, "GET", params=form_data)

            records = self._extract_table(soup)
            all_records.extend(records)
            page += 1

            if not next_selector:
                break

            next_link = soup.select_one(next_selector)
            if not next_link or not next_link.get("href"):
                break

            current_url = urljoin(url, next_link["href"])
            form_data = {}  # la paginación ya va en la URL

            if delay > 0:
                time.sleep(delay)

        return all_records

    # ------------------------------------------------------------------
    # Interfaz BaseFetcher
    # ------------------------------------------------------------------

    def _get_search_values(self) -> List[str]:
        raw_values = self.params.get("search_field_values", "")
        if raw_values:
            if isinstance(raw_values, str):
                return [v.strip() for v in raw_values.split(",") if v.strip()]
            return list(raw_values)
        return self._discover_search_values()

    def stream(self) -> Generator[List[Dict], None, None]:
        """Yields one batch of records per search value."""
        if not self.params.get("url"):
            raise ValueError("El parámetro 'url' es obligatorio")
        if not self.params.get("search_field_name"):
            raise ValueError("El parámetro 'search_field_name' es obligatorio")

        search_values = self._get_search_values()
        delay_between = float(self.params.get("delay_between_searches", 1.0))
        field_tag = self.params.get("search_field_name", "search_value")

        for i, val in enumerate(search_values):
            logger.info(f"[{i+1}/{len(search_values)}] Buscando valor: {val}")
            try:
                records = self._fetch_for_value(val)
                for r in records:
                    r.setdefault(f"_pivot_{field_tag}", val)
                logger.info(f"  → {len(records)} registros")
                if records:
                    yield records
            except Exception as exc:
                logger.error(f"  Error en valor '{val}': {exc}")
                if self.params.get("stop_on_error", False):
                    raise

            if delay_between > 0 and i < len(search_values) - 1:
                time.sleep(delay_between)

    def fetch(self) -> RawData:
        all_records: List[Dict] = []
        for chunk in self.stream():
            all_records.extend(chunk)
        logger.info(f"Fetch completado: {len(all_records)} registros totales")
        return all_records

    def parse(self, raw: RawData) -> ParsedData:
        return raw

    def normalize(self, parsed: ParsedData) -> DomainData:
        return parsed
