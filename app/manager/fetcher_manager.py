# manager/fetcher_manager.py
from factories.fetcher_factory import FetcherFactory
from factories.resolver_factory import ResolverFactory
from db import session
from models import ResolverSource

class FetcherManager:

    @staticmethod
    def run(resolver_source_id: int):
        rs = session.get(ResolverSource, resolver_source_id)

        # 1. Construir fetcher on the fly
        fetcher = FetcherFactory.build(
            fetcher_type=rs.fetcher_type,
            params=rs.params
        )

        # 2. Ejecutar extracción
        data = fetcher.execute()

        # 3. Construir resolver on the fly
        resolver = ResolverFactory.build(rs.resolver)

        # 4. Resolver dominio (core.models)
        resolver.resolve(data)
