import importlib
from typing import Dict, Optional
from app.models import Resource
from app.fetchers.base import BaseFetcher


class FetcherFactory:
    """
    Factory dinámica: instancia fetchers usando el class_path de la BD.
    Fallback a mapping estático para compatibilidad.
    """

    # Fallback estático por si el fetcher no tiene class_path en BD
    _FALLBACK = {
        "API REST": "app.fetchers.rest.RestFetcher",
        "HTML Forms": "app.fetchers.html.HtmlFetcher",
    }

    @staticmethod
    def create_from_resource(resource: Resource, execution_params: Optional[Dict] = None) -> BaseFetcher:
        if not resource.active:
            raise ValueError(f"Resource '{resource.name}' está desactivado")

        if not resource.fetcher:
            raise ValueError(f"Resource '{resource.name}' no tiene fetcher asignado")

        # Obtener class_path: primero desde BD, luego fallback estático
        class_path = resource.fetcher.class_path
        if not class_path:
            class_path = FetcherFactory._FALLBACK.get(resource.fetcher.code)
        if not class_path:
            raise ValueError(
                f"Fetcher '{resource.fetcher.code}' no tiene class_path definido"
            )

        # Importar dinámicamente
        try:
            module_path, class_name = class_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            fetcher_class = getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            raise ValueError(
                f"No se pudo cargar el fetcher '{class_path}': {e}"
            )

        # Resolution order: fetcher defaults → resource params → execution params
        params_dict = FetcherFactory._build_defaults_dict(resource.fetcher.params_def)
        params_dict.update(FetcherFactory._build_params_dict(resource.params))
        if execution_params:
            params_dict.update(execution_params)
        return fetcher_class(params_dict)

    @staticmethod
    def _build_defaults_dict(params_def: list) -> Dict[str, str]:
        result = {}
        for p in params_def:
            if p.default_value is not None:
                result[p.param_name] = str(p.default_value)
        return result

    @staticmethod
    def _build_params_dict(params: list) -> Dict[str, str]:
        return {param.key: param.value for param in params}
