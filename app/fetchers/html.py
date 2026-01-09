"""
HTML Fetcher para fuentes que devuelven HTML en lugar de JSON.
Usado para scraping de formularios web como RER del Ministerio de Justicia.
"""
import requests
from bs4 import BeautifulSoup
from app.fetchers.base import BaseFetcher, RawData, ParsedData, DomainData


class HtmlFetcher(BaseFetcher):
    """Fetcher para endpoints que devuelven HTML"""

    def __init__(self, params):
        super().__init__(params)
        self._request_metadata = {}  # Store request metadata

    def fetch(self) -> RawData:
        """Realiza el request HTTP y retorna el HTML crudo"""
        url = self.params.get("url")
        method = self.params.get("method", "GET").upper()
        timeout = int(self.params.get("timeout", 30))

        if not url:
            raise ValueError("El parámetro 'url' es obligatorio para HtmlFetcher")

        # Construir query params desde los parámetros del source
        # Excluir parámetros técnicos (url, method, timeout, headers)
        excluded_params = {"url", "method", "timeout", "headers"}
        query_params = {
            k: v for k, v in self.params.items()
            if k not in excluded_params and v  # Solo incluir si tiene valor
        }

        # Headers opcionales
        headers = self.params.get("headers", {})
        if isinstance(headers, str):
            import json
            headers = json.loads(headers)

        # Agregar User-Agent por defecto para evitar bloqueos
        if "User-Agent" not in headers:
            headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

        # Build the complete URL for metadata
        if method == "GET" and query_params:
            from urllib.parse import urlencode
            full_url = f"{url}?{urlencode(query_params)}"
        else:
            full_url = url

        # Store request metadata
        self._request_metadata = {
            "url": full_url,
            "method": method,
            "query_params": query_params,
            "headers": {k: v for k, v in headers.items() if k != "User-Agent"}  # Exclude default UA
        }

        # Hacer el request
        if method == "GET":
            response = requests.get(url, params=query_params, headers=headers, timeout=timeout)
        elif method == "POST":
            response = requests.post(url, data=query_params, headers=headers, timeout=timeout)
        else:
            response = requests.request(method, url, data=query_params, headers=headers, timeout=timeout)

        response.raise_for_status()
        return response.text

    def parse(self, raw: RawData) -> ParsedData:
        """
        Parsea el HTML usando BeautifulSoup.
        Retorna un dict con estructura básica que puede ser sobrescrita.
        """
        soup = BeautifulSoup(raw, 'html.parser')

        # Extraer información básica del HTML
        parsed = {
            "title": soup.title.string if soup.title else None,
            "html": raw,
            "soup": soup,  # Incluir el objeto soup por si necesitan acceso directo
        }

        # Intentar extraer tablas si existen (común en resultados de búsqueda)
        tables = soup.find_all('table')
        if tables:
            parsed["tables"] = []
            for table in tables:
                table_data = []
                rows = table.find_all('tr')
                for row in rows:
                    cols = row.find_all(['td', 'th'])
                    table_data.append([col.get_text(strip=True) for col in cols])
                parsed["tables"].append(table_data)

        # Intentar extraer formularios
        forms = soup.find_all('form')
        if forms:
            parsed["forms"] = []
            for form in forms:
                form_data = {
                    "action": form.get("action"),
                    "method": form.get("method", "GET"),
                    "inputs": []
                }
                inputs = form.find_all(['input', 'select', 'textarea'])
                for inp in inputs:
                    form_data["inputs"].append({
                        "name": inp.get("name"),
                        "type": inp.get("type", "text"),
                        "value": inp.get("value")
                    })
                parsed["forms"].append(form_data)

        return parsed

    def normalize(self, parsed: ParsedData) -> DomainData:
        """
        Normaliza los datos parseados a un formato de dominio.
        Por defecto retorna tal cual, pero debe ser sobrescrito
        por cada fuente específica.
        """
        # Para RER por ejemplo, aquí extraerías las entidades religiosas
        # de las tablas HTML y las convertirías a un formato estructurado

        # Por ahora retornamos lo parseado tal cual
        return {
            "source_type": "html",
            "title": parsed.get("title"),
            "raw_html_length": len(parsed.get("html", "")),
            "tables_count": len(parsed.get("tables", [])),
            "forms_count": len(parsed.get("forms", [])),
            "parsed_data": parsed
        }



