"""
Mutations GraphQL para modificar datos.
"""
import strawberry
from uuid import uuid4
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Resource, ResourceParam, FetcherType
from app.graphql.types import (
    ResourceType,
    FetcherTypeType,
    CreateResourceInput,
    UpdateResourceInput,
    CreateFetcherTypeInput,
    UpdateFetcherTypeInput,
    ExecutionResult
)
from app.graphql.queries import map_resource, map_fetcher_type
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
            # Verificar que el fetcher_type existe
            fetcher_type = db.query(FetcherType).filter(
                FetcherType.id == input.fetcher_type_id
            ).first()
            if not fetcher_type:
                raise ValueError(f"FetcherType con id '{input.fetcher_type_id}' no existe")

            # Crear Source
            source = Source(
                id=uuid4(),
                name=input.name,
                publisher=input.publisher,
                target_table=input.target_table,
                fetcher_type_id=input.fetcher_type_id,
                active=input.active
            )
            db.add(source)
            db.flush()  # Para obtener el ID

            # Crear parámetros
            for param_input in input.params:
                param = SourceParam(
                    id=uuid4(),
                    resource_id=resource.id,
                    key=param_input.key,
                    value=param_input.value
                )
                db.add(param)

            db.commit()
            db.refresh(source)
            return map_resource(source)
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
            source = db.query(Source).filter(Source.id == id).first()
            if not source:
                raise ValueError(f"Resource con id '{id}' no encontrado")

            # Actualizar campos
            if input.name is not None:
                resource.name = input.name
            if input.publisher is not None:
                resource.publisher = input.publisher
            if input.target_table is not None:
                resource.target_table = input.target_table
            if input.fetcher_type_id is not None:
                resource.fetcher_type_id = input.fetcher_type_id
            if input.active is not None:
                resource.active = input.active

            # Actualizar parámetros si se proporcionan
            if input.params is not None:
                # Eliminar parámetros existentes
                db.query(SourceParam).filter(SourceParam.source_id == resource.id).delete()

                # Crear nuevos parámetros
                for param_input in input.params:
                    param = SourceParam(
                        id=uuid4(),
                        resource_id=resource.id,
                        key=param_input.key,
                        value=param_input.value
                    )
                    db.add(param)

            db.commit()
            db.refresh(source)
            return map_resource(source)
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
            source = db.query(Source).filter(Source.id == id).first()
            if not source:
                raise ValueError(f"Resource con id '{id}' no encontrado")

            db.delete(source)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation
    def execute_resource(self, id: str) -> ExecutionResult:
        """Ejecuta un Source para actualizar sus datos"""
        db = get_db()
        try:
            source = db.query(Source).filter(Source.id == id).first()
            if not source:
                return ExecutionResult(
                    success=False,
                    message=f"Resource con id '{id}' no encontrado"
                )

            # Ejecutar el fetcher
            FetcherManager.run(db, id)

            return ExecutionResult(
                success=True,
                message=f"Source '{resource.name}' ejecutado correctamente",
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
    def create_fetcher_type(self, input: CreateFetcherTypeInput) -> FetcherTypeType:
        """Crea un nuevo tipo de fetcher"""
        db = get_db()
        try:
            # Verificar que el código no exista
            existing = db.query(FetcherType).filter(FetcherType.code == input.code).first()
            if existing:
                raise ValueError(f"FetcherType con código '{input.code}' ya existe")

            fetcher_type = FetcherType(
                id=uuid4(),
                code=input.code,
                class_path=input.class_path,
                description=input.description
            )
            db.add(fetcher_type)
            db.commit()
            db.refresh(fetcher_type)
            return map_fetcher_type(fetcher_type)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation
    def update_fetcher_type(self, id: str, input: UpdateFetcherTypeInput) -> FetcherTypeType:
        """Actualiza un tipo de fetcher existente"""
        db = get_db()
        try:
            fetcher_type = db.query(FetcherType).filter(FetcherType.id == id).first()
            if not fetcher_type:
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
                fetcher_type.code = input.code

            if input.class_path is not None:
                fetcher_type.class_path = input.class_path

            if input.description is not None:
                fetcher_type.description = input.description

            db.commit()
            db.refresh(fetcher_type)
            return map_fetcher_type(fetcher_type)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation
    def delete_fetcher_type(self, id: str) -> bool:
        """Elimina un tipo de fetcher"""
        db = get_db()
        try:
            fetcher_type = db.query(FetcherType).filter(FetcherType.id == id).first()
            if not fetcher_type:
                raise ValueError(f"FetcherType con id '{id}' no encontrado")

            # Verificar que no haya sources usando este fetcher_type
            sources_count = db.query(Source).filter(Source.fetcher_type_id == id).count()
            if sources_count > 0:
                raise ValueError(
                    f"No se puede eliminar el FetcherType porque {sources_count} "
                    f"source(s) lo están usando"
                )

            db.delete(fetcher_type)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
