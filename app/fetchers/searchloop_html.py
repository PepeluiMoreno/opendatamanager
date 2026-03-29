"""
searchloop_html.py

SearchLoopHtmlFetcher - Fetcher para buscadores HTML con tres modos de operación:

  A) Modo formulario (original):
     Pivota sobre los valores de un <select>; envía el formulario y extrae tabla.
     Parámetros: url, search_field_name, [search_field_values], rows_selector, ...

  B) Modo url_template plano (registro único por página):
     Sustituye {value} en la URL y extrae UN registro por página.
     Parámetros: url_template, search_field_values, field_selectors, ...

  C) Modo url_template + levels (scraping recursivo a profundidad arbitraria):
     Desde cada URL raíz, extrae un registro Y sigue links hacia sub-páginas,
     repitiendo el proceso nivel a nivel según la config de cada nivel.
     Parámetros: url_template, search_field_values, levels (JSON array)

     Estructura de `levels` (array de objetos, uno por nivel):
       [
         {
           // Nivel 0 (páginas raíz)
           "level_name": "comunidad",           // valor de _depth_name en el registro
           "field_selectors":      {"campo": "css"},
           "field_attr_selectors": {"campo": {"selector": "css", "attr": "href"}},
           "field_all_selectors":  {"campo": "css"},        // todos los matches, concatenados
           "field_label_selectors":{"campo": {"container": "css", "label": "Texto"}},
           "field_all_separator":  " | ",
           "inherit_fields":       ["comunidad", "email"],  // campos que heredan los hijos
           "subpage_link_selector":"css_selector",          // links a nivel siguiente
           "subpage_link_attr":    "href",
           "subpage_base_url":     "https://example.com",
           "subpage_delay":        1.5                      // segundos entre sub-páginas
         },
         {
           // Nivel 1 (sub-páginas)
           "level_name": "provincial",
           "field_selectors": {...},
           ...
           // sin subpage_link_selector → nivel hoja
         }
       ]
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
    # HTTP helpers
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
        """Descarga una URL y devuelve BeautifulSoup. Usa _request() del BaseFetcher
        (reintentos con backoff, nueva sesión en ConnectionError)."""
        hdrs = self._get_headers()
        resp = self._request(
            self.session, method.upper(), url,
            data=data, params=params, headers=hdrs,
        )
        return BeautifulSoup(resp.text, "html.parser")

    # ------------------------------------------------------------------
    # Auto-discovery de valores del <select>
    # ------------------------------------------------------------------

    def _discover_search_values(self) -> List[str]:
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
    # Extracción de tabla (modo formulario)
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
                record[key] = re.sub(r"\s+", " ", cell.get_text(strip=True))
            if record:
                data.append(record)
        return data

    # ------------------------------------------------------------------
    # Extracción de campos por selectores (modos B y C)
    # ------------------------------------------------------------------

    def _apply_level_config(self, soup: BeautifulSoup, level_cfg: Dict) -> Dict[str, Any]:
        """
        Extrae campos de `soup` usando la configuración de un nivel.
        Devuelve un dict con los campos extraídos (sin metadatos _depth/_url).
        """
        record: Dict[str, Any] = {}
        separator = level_cfg.get("field_all_separator", " | ")

        # 1. field_selectors: {"campo": "css"} → texto del primer match
        for field, selector in _parse_json_param(level_cfg.get("field_selectors", {})).items():
            el = soup.select_one(selector)
            record[field] = re.sub(r"\s+", " ", el.get_text(strip=True)) if el else None

        # 2. field_attr_selectors: {"campo": {"selector": "...", "attr": "..."}}
        for field, cfg in _parse_json_param(level_cfg.get("field_attr_selectors", {})).items():
            el = soup.select_one(cfg.get("selector", ""))
            record[field] = el.get(cfg.get("attr", "href")) if el else None

        # 3. field_all_selectors: {"campo": "css"} → todos los matches, concatenados
        for field, selector in _parse_json_param(level_cfg.get("field_all_selectors", {})).items():
            els = soup.select(selector)
            record[field] = separator.join(
                re.sub(r"\s+", " ", el.get_text(strip=True)) for el in els
            ) if els else None

        # 4. field_label_selectors: {"campo": {"container": "css", "label": "Texto"}}
        #    Busca un span/strong con ese texto y devuelve el sibling siguiente.
        for field, cfg in _parse_json_param(level_cfg.get("field_label_selectors", {})).items():
            container = soup.select_one(cfg.get("container", "body")) or soup
            label_text = cfg.get("label", "").lower()
            record[field] = None
            for span in container.find_all(["span", "strong", "b", "dt"]):
                if label_text in span.get_text(strip=True).lower():
                    sibling = span.find_next_sibling()
                    if sibling:
                        record[field] = re.sub(r"\s+", " ", sibling.get_text(strip=True))
                    break

        return record

    def _find_subpage_links(self, soup: BeautifulSoup, level_cfg: Dict, fallback_base: str) -> List[str]:
        """Devuelve la lista de URLs de sub-páginas indicadas por la config del nivel."""
        link_sel = level_cfg.get("subpage_link_selector", "")
        if not link_sel:
            return []
        link_attr = level_cfg.get("subpage_link_attr", "href")
        base_url = level_cfg.get("subpage_base_url", fallback_base)
        urls = []
        for a in soup.select(link_sel):
            href = a.get(link_attr)
            if href:
                urls.append(urljoin(base_url, href))
        return urls

    # ------------------------------------------------------------------
    # Scraping recursivo (modo C)
    # ------------------------------------------------------------------

    def _scrape_recursive(
        self,
        url: str,
        levels: List[Dict],
        depth: int,
        inherited: Dict[str, Any],
        subpage_delay: float,
    ) -> List[Dict[str, Any]]:
        """
        Descarga `url`, extrae un registro con la config del nivel `depth`,
        y recursivamente hace lo mismo con las sub-páginas si existen niveles siguientes.
        Devuelve lista plana de todos los registros (este nivel + descendientes).
        """
        if depth >= len(levels):
            return []

        level_cfg = levels[depth]

        try:
            soup = self._fetch(url)
        except Exception as exc:
            logger.error(f"[nivel {depth}] Error fetching {url}: {exc}")
            return []

        # Extraer campos de esta página
        fields = self._apply_level_config(soup, level_cfg)
        record: Dict[str, Any] = {
            **inherited,
            **fields,
            "_depth": depth,
            "_depth_name": level_cfg.get("level_name", f"level_{depth}"),
            "_url": url,
        }
        results = [record]

        # Bajar al siguiente nivel si hay config y links
        if depth + 1 < len(levels):
            next_cfg = levels[depth + 1]
            sub_urls = self._find_subpage_links(soup, level_cfg, url)
            sub_delay = float(level_cfg.get("subpage_delay", subpage_delay))

            # Campos a heredar por los hijos
            inherit_keys = level_cfg.get("inherit_fields", [])
            if isinstance(inherit_keys, str):
                inherit_keys = json.loads(inherit_keys)
            child_inherited = {k: record.get(k) for k in inherit_keys}

            logger.info(
                f"[nivel {depth}] {url} → {len(sub_urls)} sub-páginas para nivel {depth + 1}"
            )
            for i, sub_url in enumerate(sub_urls):
                sub_records = self._scrape_recursive(
                    sub_url, levels, depth + 1, child_inherited, subpage_delay
                )
                results.extend(sub_records)
                if sub_delay > 0 and i < len(sub_urls) - 1:
                    time.sleep(sub_delay)

        return results

    # ------------------------------------------------------------------
    # Fetch por valor de búsqueda
    # ------------------------------------------------------------------

    def _fetch_for_value(self, search_value: str) -> List[Dict[str, Any]]:
        url_template = self.params.get("url_template", "")
        levels_raw = self.params.get("levels", "")

        # ── Modo C: url_template + levels (recursivo) ──────────────────
        if url_template and levels_raw:
            levels = _parse_json_param(levels_raw)
            if not isinstance(levels, list):
                raise ValueError("El parámetro 'levels' debe ser un array JSON")
            page_url = url_template.replace("{value}", search_value)
            pivot_field = self.params.get("search_field_name", "valor")
            inherited = {f"_pivot_{pivot_field}": search_value}
            subpage_delay = float(self.params.get("subpage_delay", 1.5))
            return self._scrape_recursive(page_url, levels, 0, inherited, subpage_delay)

        # ── Modo B: url_template plano (registro único por página) ─────
        if url_template:
            page_url = url_template.replace("{value}", search_value)
            soup = self._fetch(page_url)
            # Usa los parámetros de nivel del fetcher directamente
            level_cfg = {
                "field_selectors":       self.params.get("field_selectors", {}),
                "field_attr_selectors":  self.params.get("field_attr_selectors", {}),
                "field_all_selectors":   self.params.get("field_all_selectors", {}),
                "field_label_selectors": self.params.get("field_label_selectors", {}),
                "field_all_separator":   self.params.get("field_all_separator", " | "),
            }
            pivot_field = self.params.get("search_field_name", "valor")
            record = {f"_pivot_{pivot_field}": search_value}
            record.update(self._apply_level_config(soup, level_cfg))
            return [record]

        # ── Modo A: formulario con paginación (comportamiento original) ─
        url = self.params["url"]
        method = self.params.get("method", "GET").upper()
        search_field_name = self.params["search_field_name"]
        next_selector = self.params.get("next_page_selector", "")
        max_pages = int(self.params.get("max_pages", 50))
        delay = float(self.params.get("delay_between_pages", 0.5))

        extra = _parse_json_param(self.params.get("extra_params", {}))
        form_data = {search_field_name: search_value, **extra}
        current_url = url
        all_records: List[Dict] = []
        page = 0

        while page < max_pages:
            soup = self._fetch(
                current_url,
                method,
                data=form_data if method == "POST" else None,
                params=form_data if method == "GET" else None,
            )
            records = self._extract_table(soup)
            all_records.extend(records)
            page += 1

            if not next_selector:
                break
            next_link = soup.select_one(next_selector)
            if not next_link or not next_link.get("href"):
                break
            current_url = urljoin(url, next_link["href"])
            form_data = {}
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
        """Yields one batch of records per pivot value."""
        url_template = self.params.get("url_template", "")
        if not url_template and not self.params.get("url"):
            raise ValueError("Se requiere 'url' o 'url_template'")
        if not url_template and not self.params.get("search_field_name"):
            raise ValueError("El parámetro 'search_field_name' es obligatorio en modo formulario")

        # Inicialización de sesión: GET previo para obtener cookies (e.g. JSESSIONID)
        session_init_url = self.params.get("session_init_url", "")
        if session_init_url:
            logger.info(f"Inicializando sesión en: {session_init_url}")
            self._fetch(session_init_url)

        search_values = self._get_search_values()
        delay_between = float(self.params.get("delay_between_searches", 1.0))
        field_tag = self.params.get("search_field_name", "search_value")
        preview_limit = int(self.params.get("_preview_limit", 0))
        total_yielded = 0

        for i, val in enumerate(search_values):
            logger.info(f"[{i+1}/{len(search_values)}] Procesando: {val}")
            try:
                records = self._fetch_for_value(val)
                logger.info(f"  → {len(records)} registros")
                if records:
                    if preview_limit:
                        remaining = preview_limit - total_yielded
                        records = records[:remaining]
                    if records:
                        yield records
                        total_yielded += len(records)
            except Exception as exc:
                logger.error(f"  Error en valor '{val}': {exc}")
                if self.params.get("stop_on_error", False):
                    raise

            if preview_limit and total_yielded >= preview_limit:
                logger.info(f"  Preview limit {preview_limit} alcanzado — parando.")
                break

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


# ------------------------------------------------------------------
# Utilidad
# ------------------------------------------------------------------

def _parse_json_param(value: Any) -> Any:
    """Parsea un parámetro que puede ser str JSON o ya un dict/list."""
    if isinstance(value, str):
        return json.loads(value) if value.strip() else {}
    return value or {}
