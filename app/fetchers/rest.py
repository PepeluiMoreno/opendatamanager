import requests
from app.fetchers.base import BaseFetcher, RawData, ParsedData, DomainData


class RESTFetcher(BaseFetcher):
    """Fetcher para APIs REST que devuelven JSON"""

    def fetch(self) -> RawData:
        """Realiza el request HTTP GET"""
        url = self.params.get("url")
        method = self.params.get("method", "GET").upper()
        headers = self.params.get("headers", {})
        timeout = int(self.params.get("timeout", 30))

        if not url:
            raise ValueError("El parámetro 'url' es obligatorio para RESTFetcher")

        # Parse headers if they're a JSON string
        if isinstance(headers, str):
            import json
            headers = json.loads(headers)

        # Make the HTTP request
        response = requests.request(method, url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.text

    def parse(self, raw: RawData) -> ParsedData:
        """Parsea el JSON"""
        import json
        return json.loads(raw)

    def normalize(self, parsed: ParsedData) -> DomainData:
        """Por defecto devuelve los datos tal cual. Sobrescribir si necesitas transformar."""
        return parsed


# Alias para compatibilidad con nombres en base de datos
RestFetcher = RESTFetcher
