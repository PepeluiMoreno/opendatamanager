from app.models import Source
from .types import RESTAPIFetcher, SOAPFetcher, CSVFetcher, WebScraperFetcher

_FETCHER_CLASSES = {
    "rest": RESTAPIFetcher,
    "soap": SOAPFetcher,
    "csv": CSVFetcher,
    "web_scraper": WebScraperFetcher,
}

class SourceFactory:
    @staticmethod
    def create(source: Source):
        if not source.active:
            raise ValueError(f"Fuente '{source.name}' está desactivada")
        fetcher_name = source.fetcher_type.name
        fetcher_cls = _FETCHER_CLASSES.get(fetcher_name)
        if not fetcher_cls:
            raise ValueError(f"Tipo de fetcher no soportado: {fetcher_name}")

        # Se pasan los parámetros del Source
        return fetcher_cls(**source.params)
