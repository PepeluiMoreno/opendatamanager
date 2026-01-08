# factories/resolver_factory.py
from importlib import import_module

class ResolverFactory:

    @staticmethod
    def build(resolver):
        module_path, class_name = resolver.class_path.rsplit(".", 1)
        module = import_module(module_path)
        cls = getattr(module, class_name)
        return cls()
