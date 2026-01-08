from factories.fetcher_factory import FetcherFactory
from factories.resolver_factory import ResolverFactory

class FetcherManager:

    @staticmethod
    def run(resolver_source):
        fetcher = FetcherFactory.create(resolver_source.source)
        data = fetcher.execute()
        resolver = ResolverFactory.create(resolver_source.resolver)
        resolver.resolve(data)
