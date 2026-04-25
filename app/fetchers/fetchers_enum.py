"""
Tipos de servicio web soportados (hardcodeados).
Estos son los únicos tipos válidos en el sistema.
"""
from enum import Enum


class FetchersEnum(Enum):
    """Tipos de fetchers soportados (valores de conveniencia)."""

    API_REST = {
        "code": "API REST",
        "class_path": "app.fetchers.rest.RestFetcher",
        "description": "API RESTful con soporte para JSON/XML"
    }

    HTML_FORM = {
        "code": "HTML Form",
        "class_path": "app.fetchers.html.HtmlFetcher",
        "description": "Formularios HTML simples con método GET/POST"
    }

    HTML_PAGINATED = {
        "code": "HTML Paginated",
        "class_path": "app.fetchers.paginated_html.PaginatedHtmlFetcher",
        "description": "Buscadores HTML con paginación automática y selectores configurables"
    }

    HTML_SEARCHLOOP = {
        "code": "HTML SearchLoop",
        "class_path": "app.fetchers.searchloop_html.SearchLoopHtmlFetcher",
        "description": "Buscadores HTML que pivotan sobre los valores de un <select>: descubre las opciones automáticamente e itera sobre cada una"
    }

    POWER_BI = {
        "code": "Power BI",
        "class_path": "app.fetchers.powerbi.PowerBIFetcher",
        "description": "Reports públicos de Power BI embebidos (API querydata con paginación DSR)"
    }

    SOAP = {
        "code": "SOAP",
        "class_path": "app.fetchers.soap.SoapFetcher",
        "description": "Servicio SOAP/WSDL — usa zeep para invocar operaciones de forma genérica"
    }

    WEB_TREE = {
        "code": "Web Tree",
        "class_path": "app.fetchers.web_tree_fetcher.WebTreeFetcher",
        "description": "Crawler de portales web clásicos. Modos: discover (infiere agrupaciones de URLs hoja por dimensiones year/month/quarter/...) y stream (descarga las URLs de un Resource hijo promovido enriqueciendo con dimensiones)."
    }

    # Futuros tipos (comentados hasta implementación)
    # FILES = {
    #     "code": "FILES",
    #     "class_path": "app.fetchers.files.FileFetcher",
    #     "description": "Archivos estáticos (CSV, Excel, etc.)"
    # }

    @classmethod
    def get_all(cls):
        """Retorna lista de todos los tipos disponibles"""
        return [
            {
                "code": member.value["code"],
                "class_path": member.value["class_path"],
                "description": member.value["description"]
            }
            for member in cls
        ]

    @classmethod
    def get_by_code(cls, code: str):
        """Busca un tipo por su código"""
        for member in cls:
            if member.value["code"] == code:
                return member.value
        return None
