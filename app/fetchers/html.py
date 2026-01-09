"""
HTML Fetcher para fuentes que devuelven HTML en lugar de JSON.
Usado para scraping de formularios web como RER del Ministerio de Justicia.
"""
import requests
from bs4 import BeautifulSoup
from app.fetchers.base import BaseFetcher, RawData, ParsedData, DomainData


class HtmlFetcher(BaseFetcher):
    """Fetcher para endpoints que devuelven HTML"""

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


class RerFetcher(HtmlFetcher):
    """
    Fetcher específico para RER (Registro de Entidades Religiosas).
    Hereda de HtmlFetcher y sobrescribe normalize() para extraer
    específicamente entidades religiosas.
    """

    def normalize(self, parsed: ParsedData) -> DomainData:
        """
        Normaliza los datos específicos de RER.
        Extrae las entidades religiosas de las tablas HTML.
        """
        soup = parsed.get("soup")
        if not soup:
            return {"entities": [], "error": "No se pudo parsear el HTML"}

        entities = []

        # Buscar la tabla de resultados (ajustar selector según la estructura real)
        # Esto es un ejemplo - necesitarías inspeccionar el HTML real de RER
        result_tables = soup.find_all('table', class_=['result', 'tabla-resultados'])

        if not result_tables and parsed.get("tables"):
            # Si no encontramos tabla específica, usar la primera tabla disponible
            result_tables = [soup.find('table')]

        for table in result_tables:
            if not table:
                continue

            rows = table.find_all('tr')
            headers = []

            # Extraer headers
            header_row = rows[0] if rows else None
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]

            # Extraer datos
            for row in rows[1:]:  # Skip header row
                cols = row.find_all('td')
                if not cols:
                    continue

                entity = {}
                for i, col in enumerate(cols):
                    header = headers[i] if i < len(headers) else f"column_{i}"
                    entity[header] = col.get_text(strip=True)

                if entity:  # Solo agregar si tiene datos
                    entities.append(entity)

        return {
            "source": "RER - Ministerio de Justicia",
            "entity_count": len(entities),
            "entities": entities,
            "search_params": {
                k: v for k, v in self.params.items()
                if k not in {"url", "method", "timeout", "headers"}
            }
        }
