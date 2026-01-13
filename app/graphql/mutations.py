"""
Mutations GraphQL para modificar datos.
"""
import strawberry
from uuid import uuid4
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Resource, ResourceParam, FetcherType, TypeFetcherParams
from app.graphql.types import (
    ResourceType,
    Fetcher,
    TypeFetcherParamType,
    CreateResourceInput,
    UpdateResourceInput,
    CreateFetcherInput,
    UpdateFetcherInput,
    CreateTypeFetcherParamInput,
    UpdateTypeFetcherParamInput,
    ExecutionResult
)
from app.graphql.queries import map_resource, map_fetcher, map_type_fetcher_param
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
    def create_fetcher(self, input: CreateFetcherInput) -> Fetcher:
        """Crea un nuevo tipo de fetcher"""
        db = get_db()
        try:
            # Verificar que el código no exista
            existing = db.query(FetcherType).filter(FetcherType.code == input.name).first()
            if existing:
                raise ValueError(f"Fetcher con nombre '{input.name}' ya existe")

            fetcher = FetcherType(
                id=uuid4(),
                code=input.name,
                class_path=input.class_path,
                description=input.description
            )
            db.add(fetcher)
            db.commit()
            db.refresh(fetcher)
            return map_fetcher(fetcher)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation
    def update_fetcher(self, id: str, input: UpdateFetcherInput) -> Fetcher:
        """Actualiza un tipo de fetcher existente"""
        db = get_db()
        try:
            fetcher = db.query(FetcherType).filter(FetcherType.id == id).first()
            if not fetcher:
                raise ValueError(f"FetcherType con id '{id}' no encontrado")

            # Actualizar campos
            if input.name is not None:
                # Verificar que el nuevo nombre no exista
                existing = db.query(FetcherType).filter(
                    FetcherType.code == input.name,
                    FetcherType.id != id
                ).first()
                if existing:
                    raise ValueError(f"Fetcher con nombre '{input.name}' ya existe")
                fetcher.code = input.name

            if input.class_path is not None:
                fetcher.class_path = input.class_path

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

    @strawberry.mutation
    def create_type_fetcher_param(self, input: CreateTypeFetcherParamInput) -> TypeFetcherParamType:
        """Crea un parámetro para un fetcher"""
        db = get_db()
        try:
            # Verificar que el fetcher existe
            fetcher = db.query(FetcherType).filter(FetcherType.id == input.fetcher_id).first()
            if not fetcher:
                raise ValueError(f"Fetcher con id '{input.fetcher_id}' no encontrado")

            param = TypeFetcherParams(
                id=uuid4(),
                fetcher_id=input.fetcher_id,
                param_name=input.param_name,
                required=input.required,
                data_type=input.data_type,
                default_value=input.default_value,
                enum_values=input.enum_values
            )
            db.add(param)
            db.commit()
            db.refresh(param)
            return map_type_fetcher_param(param)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation
    def update_type_fetcher_param(self, id: str, input: UpdateTypeFetcherParamInput) -> TypeFetcherParamType:
        """Actualiza un parámetro de fetcher"""
        db = get_db()
        try:
            param = db.query(TypeFetcherParams).filter(TypeFetcherParams.id == id).first()
            if not param:
                raise ValueError(f"TypeFetcherParam con id '{id}' no encontrado")

            if input.param_name is not None:
                param.param_name = input.param_name
            if input.required is not None:
                param.required = input.required
            if input.data_type is not None:
                param.data_type = input.data_type
            if input.default_value is not None:
                param.default_value = input.default_value
            if input.enum_values is not None:
                param.enum_values = input.enum_values

            db.commit()
            db.refresh(param)
            return map_type_fetcher_param(param)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation
    def delete_type_fetcher_param(self, id: str) -> bool:
        """Elimina un parámetro de fetcher"""
        db = get_db()
        try:
            param = db.query(TypeFetcherParams).filter(TypeFetcherParams.id == id).first()
            if not param:
                raise ValueError(f"TypeFetcherParam con id '{id}' no encontrado")

            db.delete(param)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
