"""
Manager para ejecutar fetchers y actualizar datos en BD.
"""
from sqlalchemy.orm import Session
from app.models import Resource
from app.fetchers.factory import FetcherFactory
from app.core import upsert


class FetcherManager:
    """Orquestador de ejecución de fetchers"""

    @staticmethod
    def run(session: Session, resource_id: str) -> None:
        """
        Ejecuta un Resource específico: fetch → parse → normalize → upsert

        Args:
            session: Sesión SQLAlchemy activa
            resource_id: UUID del Resource a ejecutar
        """
        # Cargar Resource con sus relaciones
        resource = session.query(Resource).filter(Resource.id == resource_id).first()

        if not resource:
            raise ValueError(f"Resource con id '{resource_id}' no encontrado")

        if not resource.active:
            print(f"⚠️  Resource '{resource.name}' está desactivado, omitiendo...")
            return

        print(f"▶️  Ejecutando Resource: {resource.name} (publisher: {resource.publisher})")

        # 1. Crear fetcher dinámicamente desde BD
        fetcher = FetcherFactory.create_from_resource(resource)

        # 2. Ejecutar pipeline completo
        data = fetcher.execute()

        # 3. Por ahora solo retornamos los datos sin guardar (no hay tabla destino definida)
        print(f"✅ Resource '{resource.name}' completado - {len(data) if isinstance(data, list) else 1} registros obtenidos")

        # TODO: Cuando se defina la tabla destino, descomentar:
        # upsert(session=session, target_model=resource.target_table, data=data)

        return data

    @staticmethod
    def run_all(session: Session) -> None:
        """
        Ejecuta todos los Resources activos.

        Args:
            session: Sesión SQLAlchemy activa
        """
        resources = session.query(Resource).filter(Resource.active == True).all()

        if not resources:
            print("⚠️  No hay resources activos para ejecutar")
            return

        print(f"🚀 Ejecutando {len(resources)} resources activos...")

        for resource in resources:
            try:
                FetcherManager.run(session, str(resource.id))
            except Exception as e:
                print(f"❌ Error en Resource '{resource.name}': {e}")
                continue

        print("✅ Ejecución completada")
