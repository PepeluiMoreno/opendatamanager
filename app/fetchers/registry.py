"""
Registro centralizado de tipos de fetchers disponibles.
Esto hace transparente el class_path para el usuario final.
"""
from typing import Dict, List


class FetcherRegistry:
    """
    Registro de fetchers disponibles en el sistema.
    Mapea códigos simples (REST, SOAP, etc.) a sus class_paths.
    """

    # Mapeo de códigos a class_paths
    _FETCHERS: Dict[str, dict] = {
        "REST": {
            "class_path": "app.fetchers.rest.RestFetcher",
            "description": "Fetcher for RESTful APIs with JSON/XML support",
            "name": "REST API"
        },
        # Aquí se pueden agregar más fetchers cuando se implementen
        # "SOAP": {
        #     "class_path": "app.fetchers.soap.SoapFetcher",
        #     "description": "Fetcher for SOAP web services",
        #     "name": "SOAP"
        # },
        # "CSV": {
        #     "class_path": "app.fetchers.csv.CsvFetcher",
        #     "description": "Fetcher for CSV files from URLs",
        #     "name": "CSV File"
        # },
    }

    @classmethod
    def get_class_path(cls, code: str) -> str:
        """Obtiene el class_path para un código de fetcher"""
        fetcher = cls._FETCHERS.get(code)
        if not fetcher:
            raise ValueError(f"Fetcher type '{code}' not found in registry")
        return fetcher["class_path"]

    @classmethod
    def get_description(cls, code: str) -> str:
        """Obtiene la descripción para un código de fetcher"""
        fetcher = cls._FETCHERS.get(code)
        if not fetcher:
            return ""
        return fetcher.get("description", "")

    @classmethod
    def get_name(cls, code: str) -> str:
        """Obtiene el nombre amigable para un código de fetcher"""
        fetcher = cls._FETCHERS.get(code)
        if not fetcher:
            return code
        return fetcher.get("name", code)

    @classmethod
    def list_available(cls) -> List[dict]:
        """Lista todos los fetchers disponibles"""
        return [
            {
                "code": code,
                "name": info.get("name", code),
                "description": info.get("description", ""),
                "class_path": info["class_path"]
            }
            for code, info in cls._FETCHERS.items()
        ]

    @classmethod
    def is_valid_code(cls, code: str) -> bool:
        """Verifica si un código de fetcher es válido"""
        return code in cls._FETCHERS

    @classmethod
    def register_fetcher(cls, code: str, class_path: str, description: str = "", name: str = None):
        """
        Registra un nuevo fetcher en el sistema.
        Útil para extensiones o plugins.
        """
        cls._FETCHERS[code] = {
            "class_path": class_path,
            "description": description,
            "name": name or code
        }
