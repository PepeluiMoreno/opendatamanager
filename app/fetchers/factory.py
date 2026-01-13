from typing import Dict
from app.models import Resource, ResourceParam
from app.fetchers.base import BaseFetcher
from app.fetchers.rest import RestFetcher
from app.fetchers.html import HtmlFetcher


class FetcherFactory:
    """
    Factory simple: mapea nombre de Fetcher a clase Python
    """

    # Mapping de nombre de fetcher a clase
    FETCHER_CLASSES = {
        "API REST": RestFetcher,
        "HTML Forms": HtmlFetcher,
    }

    @staticmethod
    def create_from_resource(resource: Resource) -> BaseFetcher:
        """
        Crea un fetcher a partir de un Resource.

        Args:
            resource: Instancia de Resource con fetcher y params cargados

        Returns:
            Instancia de BaseFetcher lista para ejecutar
        """
        if not resource.active:
            raise ValueError(f"Resource '{resource.name}' está desactivado")

        if not resource.fetcher:
            raise ValueError(f"Resource '{resource.name}' no tiene fetcher asignado")

        # Obtener clase desde mapping
        fetcher_class = FetcherFactory.FETCHER_CLASSES.get(resource.fetcher.code)
        if not fetcher_class:
            raise ValueError(f"Fetcher '{resource.fetcher.code}' no está registrado")

        # Convertir ResourceParam a diccionario
        params_dict = FetcherFactory._build_params_dict(resource.params)

        # Instanciar y devolver
        return fetcher_class(params_dict)

    @staticmethod
    def _build_params_dict(params: list) -> Dict[str, str]:
        """Convierte lista de ResourceParam a diccionario"""
        return {param.key: param.value for param in params}
