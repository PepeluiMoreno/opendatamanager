# app/resolver/factory.py
"""
/app/resolver/factory.py
Factory dinámico: lee Source y devuelve BaseResolver listo para ejecutar.
Único lugar que conoce los tipos de plugins.
"""
from typing import Type
from app.models import Source
from app.resolver.base import BaseResolver

# Mapa dinámico: código en BD → clase Python
_RESOLVER_CLASSES = {
    "rest": "app.resolver.rest_resolver.RESTResolver",
    "soap": "app.resolver.soap_resolver.SOAPResolver",
    "csv": "app.resolver.csv_resolver.CSVResolver",
    # Añade aquí nuevos tipos sin tocar el orquestador
}

def create_resolver(source: Source) -> BaseResolver:
    """
    Instancia el resolver correcto a partir de Source.params
    """
    import importlib
    fetcher_code = source.fetcher_type.code
    class_path = _RESOLVER_CLASSES.get(fetcher_code)
    if not class_path:
        raise ValueError(f"Tipo de resolver no registrado: {fetcher_code}")

    module_name, class_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_name)
    resolver_cls = getattr(module, class_name)  # type: Type[BaseResolver]

    # Instanciamos pasándole los parámetros del Source
    return resolver_cls(**source.params)