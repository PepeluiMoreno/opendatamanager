import importlib
from typing import Dict
from app.models import Resource, ResourceParam
from app.fetchers.base import BaseFetcher


class FetcherFactory:
    """
    Factory 100% dinámico: lee FetcherType.class_path desde BD
    y crea instancias sin hardcodeo de clases.
    """

    @staticmethod
    def create_from_resource(resource: Resource) -> BaseFetcher:
        """
        Crea un fetcher a partir de un Resource.

        Args:
            resource: Instancia de Resource con fetcher_type y params cargados

        Returns:
            Instancia de BaseFetcher lista para ejecutar
        """
        if not resource.active:
            raise ValueError(f"Resource '{resource.name}' está desactivado")

        if not resource.fetcher_type:
            raise ValueError(f"Resource '{resource.name}' no tiene fetcher_type asignado")

        # Obtener class_path dinámicamente desde BD
        class_path = resource.fetcher_type.class_path
        if not class_path:
            raise ValueError(f"FetcherType '{resource.fetcher_type.code}' no tiene class_path definido")

        # Convertir ResourceParam a diccionario
        params_dict = FetcherFactory._build_params_dict(resource.params)

        # Importar clase dinámicamente
        fetcher_class = FetcherFactory._import_class(class_path)

        # Instanciar y devolver
        return fetcher_class(params_dict)

    @staticmethod
    def _build_params_dict(params: list) -> Dict[str, str]:
        """Convierte lista de ResourceParam a diccionario"""
        return {param.key: param.value for param in params}

    @staticmethod
    def _import_class(class_path: str):
        """
        Importa dinámicamente una clase desde su path completo.
        Ejemplo: 'app.fetchers.rest.RESTFetcher'
        """
        try:
            module_path, class_name = class_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            fetcher_class = getattr(module, class_name)
            return fetcher_class
        except (ValueError, ModuleNotFoundError, AttributeError) as e:
            raise ImportError(f"No se pudo importar '{class_path}': {e}")
