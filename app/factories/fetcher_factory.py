from importlib import import_module

class FetcherFactory:

    @staticmethod
    def create(source):
        ft = source.fetcher_type
        module_path, class_name = ft.class_path.rsplit(".", 1)
        module = import_module(module_path)
        cls = getattr(module, class_name)
        return cls(source.params)
