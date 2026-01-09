"""
Tipos de servicio web soportados (hardcodeados).
Estos son los únicos tipos válidos en el sistema.
"""
from enum import Enum


class WebServiceType(Enum):
    """Tipos de servicios web soportados"""

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

    # Futuros tipos (comentados hasta implementación)
    # SOAP = {
    #     "code": "SOAP",
    #     "class_path": "app.fetchers.soap.SoapFetcher",
    #     "description": "Servicio SOAP/WSDL"
    # }
    #
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
