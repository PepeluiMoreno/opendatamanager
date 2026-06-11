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
        # Estado del formulario (cacheado): hidden inputs y acción descubierta.
        self._form_state_loaded = False
        self._form_hidden: Dict[str, str] = {}
        self._discovered_action: Optional[str] = None
        self._form_soup: Optional[BeautifulSoup] = None

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
               data: Optional[Dict] = None, params: Optional[Dict] = None,
               files: Optional[Dict] = None) -> BeautifulSoup:
        """Descarga una URL y devuelve BeautifulSoup. Usa _request() del BaseFetcher
        (reintentos con backoff, nueva sesión en ConnectionError).

        Si se pasa `files`, requests envía multipart/form-data (necesario para
        portales tipo Struts2 que exigen ese enctype)."""
        hdrs = self._get_headers()
        kwargs: Dict[str, Any] = {"headers": hdrs}
        if files is not None:
            kwargs["files"] = files
        else:
            kwargs["data"] = data
            kwargs["params"] = params
        resp = self._request(self.session, method.upper(), url, **kwargs)
        return BeautifulSoup(resp.text, "html.parser")

    def _ensure_form_state(self) -> None:
        """Carga (una vez) la página del formulario: cachea sus inputs hidden y la
        acción del <form> que contiene el campo de búsqueda. Establece sesión."""
        if self._form_state_loaded:
            return
        url = self.params["url"]
        soup = self._fetch(url)
        hidden: Dict[str, str] = {}
        for inp in soup.find_all("input", {"type": "hidden"}):
            name = inp.get("name")
            if name:
                hidden[name] = inp.get("value", "") or ""
        self._form_hidden = hidden
        # Acción del form que envuelve el campo de búsqueda (o el primer form).
        action = None
        field_name = self.params.get("search_field_name")
        el = soup.find(attrs={"name": field_name}) if field_name else None
        form = el.find_parent("form") if el else None
        if form is None:
            form = soup.find("form")
        if form and form.get("action"):
            action = urljoin(url, form["action"])
        self._discovered_action = action
        self._form_soup = soup
        self._form_state_loaded = True

    # ------------------------------------------------------------------
    # Auto-discovery de valores del <select>
    # ------------------------------------------------------------------

    def _discover_search_values(self) -> List[str]:
        url = self.params["url"]
        field_name = self.params["search_field_name"]
        logger.info(f"Descubriendo valores del select '{field_name}' en {url}")
        self._ensure_form_state()
        soup = self._form_soup
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

    def _extract_table(self, soup: BeautifulSoup, base_url: str = "") -> List[Dict[str, str]]:
        rows_selector = self.params.get("rows_selector", "table tr")
        rows = soup.select(rows_selector)
        if not rows:
            return []

        # Captura opcional del enlace por fila (e.g. enlace a la página de detalle).
        row_link_selector = self.params.get("row_link_selector", "")
        row_link_field = self.params.get("row_link_field", "_detail_url")

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
            if row_link_selector:
                a = row.select_one(row_link_selector)
                href = a.get("href") if a else None
                if href:
                    record[row_link_field] = urljoin(base_url, href) if base_url else href
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
        #    Busca un span/strong/b/dt con ese texto y devuelve su valor asociado:
        #    primero el sibling elemento (con soporte de listas <ul>/<ol>), y si no
        #    existe, los nodos de texto que siguen a la etiqueta (patrón
        #    `<p><strong>Etiqueta</strong>: valor</p>`, frecuente en portales Struts).
        #    Coincidencia: exacta primero (ignorando ':' final), substring después.
        for field, cfg in _parse_json_param(level_cfg.get("field_label_selectors", {})).items():
            container = soup.select_one(cfg.get("container", "body")) or soup
            label_text = cfg.get("label", "").strip().rstrip(":").lower()
            labels = container.find_all(["span", "strong", "b", "dt"])
            target = None
            for el in labels:  # pasada exacta
                if el.get_text(strip=True).rstrip(":").lower() == label_text:
                    target = el
                    break
            if target is None:
                for el in labels:  # pasada substring (compatibilidad)
                    if label_text in el.get_text(strip=True).lower():
                        target = el
                        break
            record[field] = self._label_value(target) if target is not None else None

        return record

    @staticmethod
    def _label_value(label_el) -> Optional[str]:
        """Valor asociado a una etiqueta: lista <ul>/<ol> hermana, nodos de texto
        siguientes, o texto del siguiente elemento hermano, en ese orden."""
        sibling = label_el.find_next_sibling()
        if sibling is not None and sibling.name == "table":
            filas = []
            for tr in sibling.find_all("tr"):
                celdas = [re.sub(r"\s+", " ", c.get_text(strip=True))
                          for c in tr.find_all("td")]
                if any(celdas):
                    filas.append(", ".join(c for c in celdas if c))
            return " | ".join(filas) or None
        if sibling is not None and sibling.name in ("ul", "ol"):
            items = [re.sub(r"\s+", " ", li.get_text(strip=True))
                     for li in sibling.find_all("li")]
            return " | ".join(i for i in items if i) or None
        parts = []
        for node in label_el.next_siblings:
            if getattr(node, "name", None):  # primer elemento corta la lectura de texto
                break
            parts.append(str(node))
        text = re.sub(r"\s+", " ", "".join(parts)).strip().lstrip(":").strip().strip(",").strip()
        if text:
            return text
        if sibling is not None:
            return re.sub(r"\s+", " ", sibling.get_text(strip=True)) or None
        return None

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

        # ── Modo A: formulario con paginación ───────────────────────────
        # Soporta GET simple, POST de formulario y POST tipo Struts2
        # (acción de búsqueda distinta, multipart, campo __multiselect_ y
        # arrastre de inputs hidden), según search_mode / params.
        url = self.params["url"]
        search_field_name = self.params["search_field_name"]
        next_selector = self.params.get("next_page_selector", "")
        max_pages = int(self.params.get("max_pages", 50))
        delay = float(self.params.get("delay_between_pages", 0.5))
        _preview = int(self.params.get("_preview_limit", 0) or 0)
        if _preview:
            # En preview los delays de cortesía sobran y el gateway tiene timeout
            # corto: sin esperas y con un techo de páginas holgado para el tope.
            delay = 0.0
            max_pages = min(max_pages, max(1, (_preview // 10) + 2))

        method, enctype, use_multiselect, carry_hidden = self._resolve_search_mode()
        # Acción de búsqueda: explícita > descubierta del <form> > misma url.
        if carry_hidden or self.params.get("search_action_url") in (None, ""):
            self._ensure_form_state()
        search_url = (
            self.params.get("search_action_url")
            or self._discovered_action
            or url
        )

        extra = _parse_json_param(self.params.get("extra_params", {}))
        base_fields: Dict[str, Any] = {}
        if carry_hidden:
            base_fields.update(self._form_hidden)
        base_fields.update(extra)
        base_fields[search_field_name] = search_value
        if use_multiselect:
            # Convención Struts2: campo compañero vacío por cada multiselect.
            base_fields[f"__multiselect_{search_field_name}"] = ""

        form_data = dict(base_fields)
        current_url = search_url
        all_records: List[Dict] = []
        page = 0
        preview_limit = int(self.params.get("_preview_limit", 0) or 0)

        while page < max_pages:
            soup = self._send_search(current_url, method, enctype, form_data) if form_data \
                else self._fetch(current_url)
            records = self._extract_table(soup, base_url=current_url)
            all_records.extend(records)
            page += 1

            # En preview, no seguir paginando una vez juntadas filas suficientes:
            # el enriquecimiento por detalle (caro) ya se acota aparte.
            if preview_limit and len(all_records) >= preview_limit:
                all_records = all_records[:preview_limit]
                break

            if not next_selector:
                break
            next_link = soup.select_one(next_selector)
            if not next_link or not next_link.get("href"):
                break
            nxt = urljoin(search_url, next_link["href"])
            if nxt == current_url:
                break
            current_url = nxt
            form_data = {}
            if delay > 0:
                time.sleep(delay)

        return self._enrich_with_details(all_records)

    def _enrich_with_details(self, records: List[Dict]) -> List[Dict]:
        """Enriquecimiento opcional por página de detalle (patrón listado→detalle).
        Si `detail_level` está definido (mismo esquema que un nivel de `levels`),
        visita la URL capturada por fila (`row_link_field`, por defecto
        `_detail_url`) y fusiona los campos extraídos en el registro."""
        detail_cfg = _parse_json_param(self.params.get("detail_level", {}))
        if not detail_cfg:
            return records
        preview = int(self.params.get("_preview_limit", 0) or 0)
        # En preview, el enriquecimiento por detalle (1 petición por fila) es caro
        # frente al timeout del gateway, pero el listado solo trae 4 columnas y no
        # sirve para validar el recurso. Compromiso: enriquecer unas POCAS filas
        # (preview_detail_max, def. 5) sin esperas, salvo preview_detail=false.
        if preview and str(self.params.get("preview_detail", "true")).lower() in ("0", "false", "no"):
            return records
        url_field = self.params.get("detail_url_field",
                                    self.params.get("row_link_field", "_detail_url"))
        delay = float(self.params.get("detail_delay", 1.0))
        if preview:
            delay = 0.0
            records = records[:min(preview, int(self.params.get("preview_detail_max", 5)))]
        total = len(records)
        for i, rec in enumerate(records):
            durl = rec.get(url_field)
            if not durl:
                continue
            try:
                soup = self._fetch(durl)
                rec.update(self._apply_level_config(soup, detail_cfg))
            except Exception as exc:
                logger.error(f"[detalle {i + 1}/{total}] Error en {durl}: {exc}")
                if self.params.get("stop_on_error", False):
                    raise
            if preview and i + 1 >= preview:
                break
            if delay > 0 and i < total - 1:
                time.sleep(delay)
        return records

    def _resolve_search_mode(self):
        """Resuelve (method, enctype, use_multiselect, carry_hidden) a partir de
        search_mode y/o params explícitos. Los params explícitos siempre ganan."""
        mode = (self.params.get("search_mode") or "").strip()
        method = self.params.get("method")
        enctype = self.params.get("enctype")
        multiselect = self.params.get("multiselect_companion")
        carry_hidden = self.params.get("carry_hidden_fields")

        if mode == "POST_struts":
            method = method or "POST"
            enctype = enctype or "multipart"
            multiselect = True if multiselect is None else multiselect
            carry_hidden = True if carry_hidden is None else carry_hidden
        elif mode == "POST_formulario":
            method = method or "POST"

        method = (method or "GET").upper()
        enctype = (enctype or "urlencoded").lower()
        return method, enctype, _as_bool(multiselect), _as_bool(carry_hidden)

    def _send_search(self, url: str, method: str, enctype: str, fields: Dict[str, Any]) -> BeautifulSoup:
        """Envía la búsqueda según método y enctype."""
        if method == "POST" and enctype == "multipart":
            files = {k: (None, str(v)) for k, v in fields.items()}
            return self._fetch(url, "POST", files=files)
        if method == "POST":
            return self._fetch(url, "POST", data=fields)
        return self._fetch(url, "GET", params=fields)

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
        if preview_limit:
            # En preview basta el primer pivote para validar el recurso; sin esperas.
            search_values = search_values[:1]
            delay_between = 0.0
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


def _as_bool(value: Any) -> bool:
    """Interpreta un param como booleano (acepta bool, 'true'/'1'/'yes', etc.)."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in ("true", "1", "yes", "si", "sí", "on")
