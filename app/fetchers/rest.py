import requests
import json
from app.fetchers.base import BaseFetcher, RawData, ParsedData, DomainData


class RESTFetcher(BaseFetcher):
    """Fetcher para APIs REST que devuelven JSON"""

    def fetch(self) -> RawData:
        """Realiza el request HTTP GET"""
        url = self.params.get("url")
        method = self.params.get("method", "GET").upper()
        headers = self.params.get("headers", {})
        query_params = self.params.get("query_params", {})
        timeout = int(self.params.get("timeout", 30))

        if not url:
            raise ValueError("El parámetro 'url' es obligatorio para RESTFetcher")

        # Parse headers if they're a JSON string
        if isinstance(headers, str):
            headers = json.loads(headers)

        # Parse query_params if they're a JSON string
        if isinstance(query_params, str):
            query_params = json.loads(query_params)

        # Make the HTTP request with query params
        response = requests.request(
            method,
            url,
            headers=headers,
            params=query_params,
            timeout=timeout
        )
        response.raise_for_status()
        return response.text

    def parse(self, raw: RawData) -> ParsedData:
        """Parsea el JSON"""
        return json.loads(raw)

    def normalize(self, parsed: ParsedData) -> DomainData:
        """Por defecto devuelve los datos tal cual. Sobrescribir si necesitas transformar."""
        return parsed


# Alias para compatibilidad con nombres en base de datos
RestFetcher = RESTFetcher
