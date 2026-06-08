"""
Mutations GraphQL para modificar datos.
"""
import strawberry
from uuid import uuid4
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Resource, ResourceParam, Fetcher, FetcherParams, Application, RefrescoExtemporaneo
from app.graphql_api.types import (
    ResourceType,
    FetcherType,
    FetcherParamType,
    ApplicationType,
    CreateResourceInput,
    UpdateResourceInput,
    CreateFetcherInput,
    UpdateFetcherInput,
    CreateTypeFetcherParamInput,
    UpdateTypeFetcherParamInput,
    CreateApplicationInput,
    UpdateApplicationInput,
    ExecutionResult
)
from app.graphql_api.queries import map_application, map_resource, map_fetcher, map_type_fetcher_param
from app.manager.fetcher_manager import FetcherManager
import app.scheduler as scheduler
from datetime import datetime
from sqlalchemy import func
from app.core.huella import huella_params, params_bound


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
    def create_resource(self, input: CreateResourceInput, info: strawberry.types.Info) -> ResourceType:
        """Crea una nueva fuente de datos.

        Identidad por contenido: si ya existe un recurso con la misma huella de
        params, NO se duplica; se devuelve el existente (quien lo pide queda como
        suscriptor y el dueño sigue siendo quien lo creó). Si la huella es nueva,
        se crea y el solicitante queda como dueño (created_by_id).
        """
        db = get_db()
        try:
            # Verificar que el fetcher existe
            fetcher = db.query(Fetcher).filter(
                Fetcher.id == input.fetcher_id
            ).first()
            if not fetcher:
                raise ValueError(f"Fetcher con id '{input.fetcher_id}' no existe")

            # Huella de identidad sobre los params (ver app/core/huella.py).
            # Solo se deduplica si los params están acotados; si hay alguno sin
            # valor (borrador/plantilla a rellenar), se difiere la huella (NULL).
            pares = [(p.key, p.value) for p in (input.params or [])]
            if params_bound(pares):
                ph = huella_params(pares)
                existente = db.query(Resource).filter(
                    Resource.params_hash == ph,
                    Resource.deleted_at.is_(None),
                ).first()
                if existente:
                    # Ya existe: no se duplica. El llamante se suscribe al existente.
                    return map_resource(existente)
            else:
                ph = None  # identidad sin resolver: no se deduplica todavía

            usuario = info.context.get("usuario") if (info and info.context) else None

            # Crear Resource
            resource = Resource(
                id=uuid4(),
                name=input.name,
                publisher=input.publisher,
                fetcher_id=input.fetcher_id,
                active=input.active,
                schedule=input.schedule,
                params_hash=ph,
                created_by_id=(usuario.id if usuario else None),
            )
            # Validación sintáctica de la query según su tipo (request)
            from app.services.query_validation import validar_query
            _pmap = {p.key: p.value for p in (input.params or [])}
            _err = validar_query(_pmap.get("request"), _pmap.get("query"))
            if _err:
                raise ValueError(_err)

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
            scheduler.sync_schedule(str(resource.id), resource.schedule)
            return map_resource(resource)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation
    def update_resource(self, id: str, input: UpdateResourceInput, info: strawberry.types.Info) -> ResourceType:
        """Actualiza una fuente de datos existente.

        Solo el creador (created_by_id) puede cambiar el `schedule` de refresco.
        Los suscriptores consumen la cadencia establecida o piden un refresco a
        demanda (que consume su cuota). Si se cambian los params, se recalcula la
        huella de identidad y se rechaza si colisiona con otro recurso.
        """
        db = get_db()
        try:
            resource = db.query(Resource).filter(Resource.id == id).first()
            if not resource:
                raise ValueError(f"Resource con id '{id}' no encontrado")

            usuario = info.context.get("usuario") if (info and info.context) else None
            # Autoridad del schedule: solo el creador puede cambiar la cadencia.
            if input.schedule is not None and (input.schedule or None) != resource.schedule:
                if resource.created_by_id is not None and (usuario is None or usuario.id != resource.created_by_id):
                    raise ValueError(
                        "Solo el creador del recurso puede cambiar su schedule de refresco. "
                        "Los suscriptores consumen la cadencia establecida o piden un refresco "
                        "a demanda (con cuota)."
                    )

            if usuario:
                resource.updated_by_id = usuario.id

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
            if input.schedule is not None:
                resource.schedule = input.schedule if input.schedule != "" else None

            # Actualizar parámetros si se proporcionan
            if input.params is not None:
                # Validación sintáctica de la query según su tipo (request)
                from app.services.query_validation import validar_query
                _pmap = {p.key: p.value for p in input.params}
                _err = validar_query(_pmap.get("request"), _pmap.get("query"))
                if _err:
                    raise ValueError(_err)

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

                # Recalcular la huella de identidad (solo si los params están
                # acotados) y comprobar colisión con otro recurso.
                _pares = [(p.key, p.value) for p in input.params]
                if params_bound(_pares):
                    nph = huella_params(_pares)
                    colision = db.query(Resource).filter(
                        Resource.params_hash == nph,
                        Resource.id != resource.id,
                        Resource.deleted_at.is_(None),
                    ).first()
                    if colision:
                        raise ValueError(
                            f"Esos params coinciden con otro recurso existente ('{colision.name}'); "
                            "editar la identidad crearía un duplicado. Crea un recurso nuevo o "
                            "suscríbete al existente."
                        )
                    resource.params_hash = nph
                else:
                    resource.params_hash = None  # identidad sin resolver

            db.commit()
            db.refresh(resource)
            scheduler.sync_schedule(str(resource.id), resource.schedule)
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
    def execute_resource(self, id: str, info: strawberry.types.Info, params: Optional[strawberry.scalars.JSON] = None) -> ExecutionResult:
        """Ejecuta un Resource para actualizar sus datos.

        Args:
            id: UUID del Resource
            params: Parámetros runtime opcionales (clave-valor) que sobreescriben/amplían
                    los ResourceParam estáticos definidos en el recurso. Ejemplo:
                    { "año": "2023", "fechaDesde": "2023-01-01" }
        """
        db = get_db()
        try:
            resource = db.query(Resource).filter(Resource.id == id).first()
            if not resource:
                return ExecutionResult(
                    success=False,
                    message=f"Resource con id '{id}' no encontrado"
                )

            # Refresco a demanda: requiere principal autenticado y consume cuota diaria.
            usuario = info.context.get("usuario") if (info and info.context) else None
            if usuario is None:
                return ExecutionResult(success=False, resource_id=id,
                    message="El refresco a demanda requiere autenticacion (usuario/aplicacion).")
            cuota = getattr(usuario, "cuota_refrescos_diaria", 0) or 0
            inicio_dia = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            usados = db.query(func.count(RefrescoExtemporaneo.id)).filter(
                RefrescoExtemporaneo.created_by_id == usuario.id,
                RefrescoExtemporaneo.created_at >= inicio_dia,
            ).scalar() or 0
            if usados >= cuota:
                return ExecutionResult(success=False, resource_id=id,
                    message=f"Cuota diaria de refrescos a demanda agotada ({usados}/{cuota}). "
                            "El recurso se refresca segun su schedule; reintenta manana o solicita mas cuota.")
            db.add(RefrescoExtemporaneo(resource_id=resource.id, created_by_id=usuario.id))
            db.commit()

            # Ejecutar el fetcher con params runtime opcionales
            FetcherManager.run(db, id, execution_params=params)

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
    def create_fetcher(self, input: CreateFetcherInput) -> FetcherType:
        """Crea un nuevo tipo de fetcher"""
        db = get_db()
        try:
            # Verificar que el código no exista
            existing = db.query(Fetcher).filter(Fetcher.code == input.name).first()
            if existing:
                raise ValueError(f"Fetcher con nombre '{input.name}' ya existe")

            fetcher = Fetcher(
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
    def update_fetcher(self, id: str, input: UpdateFetcherInput) -> FetcherType:
        """Actualiza un tipo de fetcher existente"""
        db = get_db()
        try:
            fetcher = db.query(Fetcher).filter(Fetcher.id == id).first()
            if not fetcher:
                raise ValueError(f"Fetcher con id '{id}' no encontrado")

            # Actualizar campos
            if input.name is not None:
                # Verificar que el nuevo nombre no exista
                existing = db.query(Fetcher).filter(
                    Fetcher.code == input.name,
                    Fetcher.id != id
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
            fetcher = db.query(Fetcher).filter(Fetcher.id == id).first()
            if not fetcher:
                raise ValueError(f"Fetcher con id '{id}' no encontrado")

            # Verificar que no haya resources usando este fetcher
            resources_count = db.query(Resource).filter(Resource.fetcher_id == id).count()
            if resources_count > 0:
                raise ValueError(
                    f"No se puede eliminar el Fetcher porque {resources_count} "
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
    def create_type_fetcher_param(self, input: CreateTypeFetcherParamInput) -> FetcherParamType:
        """Crea un parámetro para un fetcher"""
        db = get_db()
        try:
            # Verificar que el fetcher existe
            fetcher = db.query(Fetcher).filter(Fetcher.id == input.fetcher_id).first()
            if not fetcher:
                raise ValueError(f"Fetcher con id '{input.fetcher_id}' no encontrado")

            param = FetcherParams(
                id=uuid4(),
                fetcher_id=input.fetcher_id,
                param_name=input.param_name,
                required=input.required,
                data_type=input.data_type,
                default_value=input.default_value,
                enum_values=input.enum_values,
                description=input.description,
                group=input.group,
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
    def update_type_fetcher_param(self, id: str, input: UpdateTypeFetcherParamInput) -> FetcherParamType:
        """Actualiza un parámetro de fetcher"""
        db = get_db()
        try:
            param = db.query(FetcherParams).filter(FetcherParams.id == id).first()
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
            if input.description is not None:
                param.description = input.description
            if input.group is not None:
                param.group = input.group

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
            param = db.query(FetcherParams).filter(FetcherParams.id == id).first()
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

    @strawberry.mutation
    def create_application(self, input: CreateApplicationInput) -> ApplicationType:
        """Crea una nueva Application"""
        db = get_db()
        try:
            application = Application(
                id=uuid4(),
                name=input.name,
                description=input.description,
                models_path=input.models_path,
                subscribed_projects=input.subscribed_projects,
                active=input.active,
                consumption_mode=input.consumption_mode or "webhook",
            )
            db.add(application)
            db.commit()
            db.refresh(application)
            return map_application(application)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation
    def update_application(self, id: str, input: UpdateApplicationInput) -> ApplicationType :           
        """Actualiza una Application existente"""
        db = get_db()
        try:
            application = db.query(Application).filter(Application.id == id).first()
            if not application:
                raise ValueError(f"Application con id '{id}' no encontrada")

            # Actualizar campos
            if input.name is not None:
                application.name = input.name
            if input.description is not None:
                application.description = input.description
            if input.models_path is not None:
                application.models_path = input.models_path
            if input.subscribed_projects is not None:
                application.subscribed_projects = input.subscribed_projects
            if input.consumption_mode is not None:
                application.consumption_mode = input.consumption_mode

            db.commit()
            db.refresh(application)
            return map_application(application)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation
    def delete_application(self, id: str) -> bool:          
        """Elimina una Application"""
        db = get_db()
        try:
            application = db.query(Application).filter(Application.id == id).first()
            if not application:
                raise ValueError(f"Application con id '{id}' no encontrada")

            db.delete(application)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation
    def activate_application(self, id: str, active: bool) -> ApplicationType:          
        """Activa o desactiva una Application"""
        db = get_db()
        try:
            application = db.query(Application).filter(Application.id == id).first()
            if not application:
                raise ValueError(f"Application con id '{id}' no encontrada")

            application.active = active
            db.commit()
            db.refresh(application)
            return map_application(application)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()      

    @strawberry.mutation
    def set_application_webhook(self, id: str, webhook_url: str, webhook_secret: str) -> ApplicationType:          
        """Configura el webhook de una Application"""
        db = get_db()
        try:
            application = db.query(Application).filter(Application.id == id).first()
            if not application:
                raise ValueError(f"Application con id '{id}' no encontrada")

            application.webhook_url = webhook_url
            application.webhook_secret = webhook_secret
            db.commit()
            db.refresh(application)
            return map_application(application)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()      

    @strawberry.mutation
    def remove_application_webhook(self, id: str) -> ApplicationType:          
        """Elimina el webhook de una Application"""
        db = get_db()
        try:
            application = db.query(Application).filter(Application.id == id).first()
            if not application:
                raise ValueError(f"Application con id '{id}' no encontrada")

            application.webhook_url = None
            application.webhook_secret = None
            db.commit()
            db.refresh(application)
            return map_application(application)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()      
            
        
