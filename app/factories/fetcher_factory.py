# factories/fetcher_factory.py
from importlib import import_module

class FetcherFactory:

    @staticmethod
    def build(fetcher_type, params: dict):
        module_path, class_name = fetcher_type.class_path.rsplit(".", 1)
        module = import_module(module_path)
        cls = getattr(module, class_name)
        return cls(params)

