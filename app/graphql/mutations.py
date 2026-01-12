"""
Mutations GraphQL para modificar datos.
"""
import strawberry
from uuid import uuid4
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Resource, ResourceParam, FetcherType
from app.fetchers.registry import FetcherRegistry
from app.graphql.types import (
    ResourceType,
    Fetcher,
    CreateResourceInput,
    UpdateResourceInput,
    CreateFetcherTypeInput,
    UpdateFetcherTypeInput,
    ExecutionResult
)
from app.graphql.queries import map_resource, map_fetcher
from app.manager.fetcher_manager import FetcherManager


def get_db():
    """Helper para obtener sesión de BD"""
    db = SessionLocal()
    try:
        return db
    finally:
        pass


@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_resource(self, input: CreateResourceInput) -> ResourceType:
        """Crea una nueva fuente de datos"""
        db = get_db()
        try:
            # Verificar que el fetcher existe
            fetcher = db.query(FetcherType).filter(
                FetcherType.id == input.fetcher_id
            ).first()
            if not fetcher:
                raise ValueError(f"FetcherType con id '{input.fetcher_id}' no existe")

            # Crear Resource
            resource = Resource(
                id=uuid4(),
                name=input.name,
                publisher=input.publisher,
                target_table=input.target_table,
                fetcher_id=input.fetcher_id,
                active=input.active
            )
            db.add(resource)
            db.flush()  # Para obtener el ID

            # Crear parámetros
            for param_input in input.params:
                param = ResourceParam(
                    id=uuid4(),
                    resource_id=resource.id,
                    key=param_input.key,
                    value=param_input.value
                )
                db.add(param)

            db.commit()
            db.refresh(resource)
            return map_resource(resource)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation
    def update_resource(self, id: str, input: UpdateResourceInput) -> ResourceType:
        """Actualiza una fuente de datos existente"""
        db = get_db()
        try:
            resource = db.query(Resource).filter(Resource.id == id).first()
            if not resource:
                raise ValueError(f"Resource con id '{id}' no encontrado")

            # Actualizar campos
            if input.name is not None:
                resource.name = input.name
            if input.publisher is not None:
                resource.publisher = input.publisher
            if input.target_table is not None:
                resource.target_table = input.target_table
            if input.fetcher_id is not None:
                resource.fetcher_id = input.fetcher_id
            if input.active is not None:
                resource.active = input.active

            # Actualizar parámetros si se proporcionan
            if input.params is not None:
                # Eliminar parámetros existentes
                db.query(ResourceParam).filter(ResourceParam.resource_id == resource.id).delete()

                # Crear nuevos parámetros
                for param_input in input.params:
                    param = ResourceParam(
                        id=uuid4(),
                        resource_id=resource.id,
                        key=param_input.key,
                        value=param_input.value
                    )
                    db.add(param)

            db.commit()
            db.refresh(resource)
            return map_resource(resource)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation
    def delete_resource(self, id: str) -> bool:
        """Elimina una fuente de datos"""
        db = get_db()
        try:
            resource = db.query(Resource).filter(Resource.id == id).first()
            if not resource:
                raise ValueError(f"Resource con id '{id}' no encontrado")

            db.delete(resource)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation
    def execute_resource(self, id: str) -> ExecutionResult:
        """Ejecuta un Resource para actualizar sus datos"""
        db = get_db()
        try:
            resource = db.query(Resource).filter(Resource.id == id).first()
            if not resource:
                return ExecutionResult(
                    success=False,
                    message=f"Resource con id '{id}' no encontrado"
                )

            # Ejecutar el fetcher
            FetcherManager.run(db, id)

            return ExecutionResult(
                success=True,
                message=f"Resource '{resource.name}' ejecutado correctamente",
                resource_id=str(resource.id)
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Error al ejecutar Source: {str(e)}",
                resource_id=id
            )
        finally:
            db.close()

    @strawberry.mutation
    def execute_all_resources(self) -> ExecutionResult:
        """Ejecuta todos los Sources activos"""
        db = get_db()
        try:
            FetcherManager.run_all(db)
            return ExecutionResult(
                success=True,
                message="Todos los resources activos ejecutados correctamente"
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Error al ejecutar resources: {str(e)}"
            )
        finally:
            db.close()

    @strawberry.mutation
    def create_fetcher(self, input: CreateFetcherTypeInput) -> Fetcher:
        """Crea un nuevo tipo de fetcher"""
        db = get_db()
        try:
            # Verificar que el código no exista
            existing = db.query(FetcherType).filter(FetcherType.code == input.code).first()
            if existing:
                raise ValueError(f"FetcherType con código '{input.code}' ya existe")

            fetcher = FetcherType(
                id=uuid4(),
                code=input.code,
                description=input.description
            )
            db.add(fetcher)
            db.commit()
            db.refresh(fetcher)
            # Register class_path in runtime registry if provided
            if getattr(input, "class_path", None):
                try:
                    FetcherRegistry.register_fetcher(input.code, input.class_path, input.description or input.code)
                except Exception:
                    # don't fail DB creation if registry registration isn't possible
                    pass
            return map_fetcher(fetcher)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation
    def update_fetcher(self, id: str, input: UpdateFetcherTypeInput) -> Fetcher:
        """Actualiza un tipo de fetcher existente"""
        db = get_db()
        try:
            fetcher = db.query(FetcherType).filter(FetcherType.id == id).first()
            if not fetcher:
                raise ValueError(f"FetcherType con id '{id}' no encontrado")

            # Actualizar campos
            if input.code is not None:
                # Verificar que el nuevo código no exista
                existing = db.query(FetcherType).filter(
                    FetcherType.code == input.code,
                    FetcherType.id != id
                ).first()
                if existing:
                    raise ValueError(f"FetcherType con código '{input.code}' ya existe")
                fetcher.code = input.code

            if input.class_path is not None:
                # class_path is not stored in DB (dropped by migration).
                # If provided, register it in the runtime registry so
                # other parts of the app can resolve it by `code`.
                try:
                    FetcherRegistry.register_fetcher(fetcher.code, input.class_path, input.description or fetcher.code)
                except Exception:
                    pass

            if input.description is not None:
                fetcher.description = input.description

            db.commit()
            db.refresh(fetcher)
            return map_fetcher(fetcher)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation
    def delete_fetcher(self, id: str) -> bool:
        """Elimina un tipo de fetcher"""
        db = get_db()
        try:
            fetcher = db.query(FetcherType).filter(FetcherType.id == id).first()
            if not fetcher:
                raise ValueError(f"FetcherType con id '{id}' no encontrado")

            # Verificar que no haya resources usando este fetcher
            resources_count = db.query(Resource).filter(Resource.fetcher_id == id).count()
            if resources_count > 0:
                raise ValueError(
                    f"No se puede eliminar el FetcherType porque {resources_count} "
                    f"resource(s) lo están usando"
                )

            db.delete(fetcher)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
