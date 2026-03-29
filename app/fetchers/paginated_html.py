"""
PaginatedHtmlFetcher - Fetcher especializado para buscadores HTML con paginación.

Diseñado específicamente para casos como el buscador de entidades religiosas
del Ministerio de Justicia que devuelven resultados paginados.
"""
import requests
from urllib.parse import urlencode, urljoin, urlparse
from bs4 import BeautifulSoup
from typing import Dict, Generator, List, Any, Optional
import time
import logging
from app.fetchers.base import BaseFetcher, RawData, ParsedData, DomainData

logger = logging.getLogger(__name__)


class PaginatedHtmlFetcher(BaseFetcher):
    """
    Fetcher para buscadores HTML con soporte para:
    - Paginación automática
    - Extracción flexible mediante selectores CSS
    - Configuración de headers y delays
    - Manejo de diferentes tipos de paginación
    """

    def __init__(self, params):
        super().__init__(params)
        self.session = requests.Session()
        self._request_metadata = {}

    def _validate_params(self):
        """Valida parámetros obligatorios"""
        required_params = ["url", "rows_selector"]
        missing = [p for p in required_params if not self.params.get(p)]
        if missing:
            raise ValueError(f"Parámetros obligatorios faltantes: {missing}")

    def _get_headers(self) -> Dict[str, str]:
        """Construye headers para requests"""
        headers = self.params.get("headers", {})
        if isinstance(headers, str):
            import json
            headers = json.loads(headers)

        # Headers por defecto para evitar bloqueos
        default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        # Combinar headers (params sobre escriben defaults)
        return {**default_headers, **headers}

    def _extract_pagination_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extrae información de paginación del HTML usando selectores configurados.
        """
        pagination_info = {
            "has_next": False,
            "has_prev": False,
            "current_page": 1,
            "total_pages": 1,
            "total_records": None,
            "next_page_url": None,
            "prev_page_url": None,
            "pagination_type": "unknown"
        }

        # 1. Buscar información textual de registros (ej: "Mostrando 1-10 de 14836")
        total_text_selectors = self.params.get("total_text_selector", [])
        for selector in total_text_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                # Parsear patrones como "1-10 de 14836", "Resultados: 14836", etc.
                import re
                total_match = re.search(r'(\d+[\s-]*)?\d+\s+de\s+(\d+)', text, re.IGNORECASE)
                if total_match:
                    pagination_info["total_records"] = int(total_match.group(2))
                
                page_match = re.search(r'página\s+(\d+)', text, re.IGNORECASE)
                if page_match:
                    pagination_info["current_page"] = int(page_match.group(1))
                break

        # 2. Buscar links de paginación (next/prev)
        pagination_type = self.params.get("pagination_type", "links")
        
        if pagination_type == "links":
            # Links explícitos de siguiente/anterior
            next_selectors = self.params.get("next_page_selector", [])
            prev_selectors = self.params.get("prev_page_selector", [])
            
            for selector in next_selectors:
                next_link = soup.select_one(selector)
                if next_link:
                    href = next_link.get("href")
                    if href:
                        pagination_info["next_page_url"] = urljoin(self.params["url"], href)
                        pagination_info["has_next"] = True
                        break

            for selector in prev_selectors:
                prev_link = soup.select_one(selector)
                if prev_link:
                    href = prev_link.get("href")
                    if href:
                        pagination_info["prev_page_url"] = urljoin(self.params["url"], href)
                        pagination_info["has_prev"] = True
                        break

        elif pagination_type == "form":
            # Paginación via form con hidden inputs
            next_form_selectors = self.params.get("next_form_selector", [])
            for selector in next_form_selectors:
                form = soup.select_one(selector)
                if form:
                    # Extraer todos los inputs del form
                    inputs = {}
                    for inp in form.find_all(['input', 'select']):
                        name = inp.get("name")
                        value = inp.get("value", "")
                        if name:
                            inputs[name] = value
                    
                    # Modificar parámetro de página si existe
                    page_param = self.params.get("page_param", "pagina")
                    current_page = int(inputs.get(page_param, 1))
                    inputs[page_param] = str(current_page + 1)
                    
                    # Construir URL del form action
                    action = form.get("action", self.params["url"])
                    pagination_info["next_page_url"] = urljoin(self.params["url"], action)
                    pagination_info["next_page_form"] = inputs
                    pagination_info["has_next"] = True
                    break

        # 3. Calcular total de páginas si tenemos total de registros
        if pagination_info["total_records"]:
            page_size = int(self.params.get("page_size", 10))
            pagination_info["total_pages"] = -(-pagination_info["total_records"] // page_size)  # Techo

        pagination_info["pagination_type"] = pagination_type
        return pagination_info

    def _extract_table_data(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """
        Extrae datos de tablas usando selectores configurados.
        """
        rows_selector = self.params.get("rows_selector", "table tr")
        rows = soup.select(rows_selector)
        
        if not rows:
            return []

        # Determinar si la primera fila es header
        has_header = self.params.get("has_header", True)
        headers = []
        start_idx = 0

        if has_header and rows:
            header_row = rows[0]
            header_selectors = self.params.get("header_selectors", ["th", "td"])
            for selector in header_selectors:
                headers = [cell.get_text(strip=True) for cell in header_row.select(selector)]
                if headers:  # Usar el primer selector que funcione
                    break
            start_idx = 1

        # Si no hay headers, generar nombres genéricos
        if not headers and rows:
            first_row = rows[start_idx] if start_idx < len(rows) else rows[0]
            cells = first_row.select("td")
            headers = [f"column_{i}" for i in range(len(cells))]

        # Extraer datos de las filas
        data = []
        for row in rows[start_idx:]:
            cells = row.select("td")
            if not cells:
                continue

            row_data = {}
            for i, cell in enumerate(cells):
                field_name = headers[i] if i < len(headers) else f"column_{i}"
                
                # Aplicar limpieza de texto si se configuró
                text = cell.get_text(strip=True)
                if self.params.get("clean_html", True):
                    # Limpiar HTML y normalizar espacios
                    import re
                    text = re.sub(r'\s+', ' ', text)
                
                row_data[field_name] = text

            # Agregar metadata de la fila si se configuró
            if self.params.get("include_row_metadata", False):
                row_data["_row_index"] = len(data)
                row_data["_row_html"] = [str(cell) for cell in cells]

            if row_data:  # Solo agregar si tiene datos
                data.append(row_data)

        return data

    def _fetch_page(self, url: str, method: str = "GET", form_data: Optional[Dict] = None) -> BeautifulSoup:
        """
        Fetch de una página específica.
        """
        timeout = int(self.params.get("timeout", 30))
        headers = self._get_headers()

        if method == "POST" and form_data:
            response = self._request(self.session, "POST", url, data=form_data, headers=headers, timeout=timeout)
        else:
            response = self._request(self.session, "GET", url, headers=headers, timeout=timeout)

        response.raise_for_status()

        # Verificar que no tengamos página de error
        if error_selectors := self.params.get("error_selectors", []):
            soup = BeautifulSoup(response.text, 'html.parser')
            for selector in error_selectors:
                if soup.select_one(selector):
                    raise ValueError(f"Error page detected with selector: {selector}")

        return BeautifulSoup(response.text, 'html.parser')

    def _apply_transformations(self, records: List[Dict]) -> List[Dict]:
        transformations = self.params.get("field_transformations", {})
        if not transformations:
            return records
        for record in records:
            for field, transform in transformations.items():
                if field in record:
                    if transform == "trim":
                        record[field] = record[field].strip()
                    elif transform == "upper":
                        record[field] = record[field].upper()
                    elif transform == "lower":
                        record[field] = record[field].lower()
        return records

    def stream(self) -> Generator[List[Dict], None, None]:
        """Yields one page of records at a time (already transformed)."""
        self._validate_params()

        url = self.params["url"]
        method = self.params.get("method", "GET").upper()
        max_pages = int(self.params.get("max_pages", 100))
        delay_between_pages = float(self.params.get("delay_between_pages", 1.0))

        current_url = url
        current_page = 1
        pagination_info = None

        logger.info(f"Starting paginated stream from {url}")

        while current_page <= max_pages:
            logger.info(f"Fetching page {current_page}: {current_url}")

            if self.params.get("pagination_type") == "form" and pagination_info and pagination_info.get("next_page_form"):
                soup = self._fetch_page(current_url, "POST", pagination_info["next_page_form"])
            else:
                soup = self._fetch_page(current_url, method)

            page_data = self._apply_transformations(self._extract_table_data(soup))
            logger.info(f"Extracted {len(page_data)} records from page {current_page}")

            if page_data:
                yield page_data

            pagination_info = self._extract_pagination_info(soup)
            if not pagination_info["has_next"]:
                logger.info("No more pages available")
                break

            if pagination_info.get("next_page_url"):
                current_url = pagination_info["next_page_url"]
            else:
                logger.warning("Has next page but no URL found, stopping")
                break

            current_page += 1
            if delay_between_pages > 0:
                time.sleep(delay_between_pages)

    def fetch(self) -> RawData:
        all_data: List[Dict] = []
        for chunk in self.stream():
            all_data.extend(chunk)
        self._request_metadata = {
            "url": self.params["url"],
            "total_records": len(all_data),
        }
        logger.info(f"Fetch completed: {len(all_data)} records")
        return all_data

    def parse(self, raw: RawData) -> ParsedData:
        return {"data": raw, "metadata": self._request_metadata, "source_type": "paginated_html"}

    def normalize(self, parsed: ParsedData) -> DomainData:
        return parsed.get("data", [])