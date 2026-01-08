# app/resolver/resolver_runner.py
"""
/app/resolver/resolver_runner.py
Ejecuta un resolver: fetch → parse → normalize → upsert
"""
from app.resolver.factory import create_resolver  # ← factory dinámico
from app.core import upsert

class ResolverRunner:
    def __init__(self, source: Source, session: Session):
        self.source = source
        self.session = session

    def run(self) -> None:
        resolver = create_resolver(self.source)  # ← factory
        data = resolver.run()  # ciclo BaseResolver
        upsert(session=self.session, target_model=self.source.project, data=data)
        print(f"✅ Resolver {self.source.name} OK")