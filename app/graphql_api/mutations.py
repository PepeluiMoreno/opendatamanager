"""
Mutations GraphQL para modificar datos.
"""
import strawberry
import threading
import ctypes
from typing import Optional, List
from uuid import uuid4
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Resource, ResourceParam, Fetcher, FetcherParams, Application, ResourceExecution, AppConfig, DerivedDatasetConfig
from datetime import datetime

# Global registry: execution_id (str) → Thread
_running_threads: dict[str, threading.Thread] = {}
_registry_lock = threading.Lock()


class ExecutionAborted(Exception):
    pass


def _kill_thread(thread: threading.Thread):
    """Raise ExecutionAborted inside a running thread via ctypes."""
    if not thread.is_alive():
        return
    tid = thread.ident
    if tid is None:
        return
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
        ctypes.c_ulong(tid),
        ctypes.py_object(ExecutionAborted),
    )
    return res  # 1 = success, 0 = thread not found
from app.graphql_api.types import (
    AppConfigType,
    SetConfigInput,
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
    ExecutionResult,
    DerivedDatasetConfigType,
    CreateDerivedDatasetConfigInput,
    UpdateDerivedDatasetConfigInput,
)
from app.graphql_api.queries import map_application, map_resource, map_fetcher, map_type_fetcher_param, map_derived_dataset_config
from app.manager.fetcher_manager import FetcherManager
import app.scheduler as scheduler


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
            fetcher = db.query(Fetcher).filter(
                Fetcher.id == input.fetcher_id
            ).first()
            if not fetcher:
                raise ValueError(f"Fetcher con id '{input.fetcher_id}' no existe")

            # Crear Resource
            resource = Resource(
                id=uuid4(),
                name=input.name,
                publisher=input.publisher,
                fetcher_id=input.fetcher_id,
                active=input.active,
                schedule=input.schedule,
            )
            db.add(resource)
            db.flush()  # Para obtener el ID

            # Crear parámetros
            for param_input in input.params:
                param = ResourceParam(
                    id=uuid4(),
                    resource_id=resource.id,
                    key=param_input.key,
                    value=param_input.value,
                    is_external=param_input.is_external or False
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
            if input.schedule is not None:
                resource.schedule = input.schedule if input.schedule != "" else None

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
                        value=param_input.value,
                        is_external=param_input.is_external or False
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
    def execute_resource(self, id: str, params: Optional[strawberry.scalars.JSON] = None) -> ExecutionResult:
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
                return ExecutionResult(success=False, message=f"Resource con id '{id}' no encontrado")
            resource_name = resource.name
            resource_id = str(resource.id)

            # Enforce max_concurrent_processes limit
            cfg = db.query(AppConfig).filter(AppConfig.key == "max_concurrent_processes").first()
            max_concurrent = int(cfg.value) if cfg else 3
            running_count = db.query(ResourceExecution).filter(
                ResourceExecution.status == "running",
                ResourceExecution.deleted_at == None,
            ).count()
            if running_count >= max_concurrent:
                return ExecutionResult(
                    success=False,
                    message=f"Max concurrent processes reached ({running_count}/{max_concurrent}). Wait for a slot to free up.",
                    resource_id=resource_id,
                )
        except Exception as e:
            return ExecutionResult(success=False, message=str(e), resource_id=id)
        finally:
            db.close()

        # Create the execution record now (before the thread) so it is immediately
        # visible in the DB and we can register the thread against a known ID.
        pre_db = SessionLocal()
        try:
            pre_exec = ResourceExecution(
                resource_id=resource_id,
                status="running",
                started_at=datetime.utcnow(),
                execution_params=params,
            )
            pre_db.add(pre_exec)
            pre_db.commit()
            execution_id = str(pre_exec.id)
        except Exception as e:
            pre_db.rollback()
            return ExecutionResult(success=False, message=f"Could not create execution record: {e}", resource_id=resource_id)
        finally:
            pre_db.close()

        def _run():
            bg_db = SessionLocal()
            try:
                FetcherManager.run(bg_db, resource_id, execution_params=params, execution_id=execution_id)
            except ExecutionAborted:
                try:
                    ex = bg_db.query(ResourceExecution).filter(
                        ResourceExecution.id == execution_id
                    ).first()
                    if ex:
                        ex.status = "aborted"
                        ex.completed_at = datetime.utcnow()
                        bg_db.commit()
                except Exception:
                    pass
            except Exception as exc:
                # Last-resort: mark as failed if FetcherManager didn't handle it
                try:
                    ex = bg_db.query(ResourceExecution).filter(
                        ResourceExecution.id == execution_id
                    ).first()
                    if ex and ex.status == "running":
                        ex.status = "failed"
                        ex.error_message = str(exc)
                        ex.completed_at = datetime.utcnow()
                        bg_db.commit()
                except Exception:
                    pass
            finally:
                bg_db.close()
                with _registry_lock:
                    _running_threads.pop(execution_id, None)

        t = threading.Thread(target=_run, daemon=True, name=f"fetcher-{resource_id[:8]}")
        t.start()

        # Register thread immediately — execution record already exists in DB
        with _registry_lock:
            _running_threads[execution_id] = t

        return ExecutionResult(
            success=True,
            message=f"Resource '{resource_name}' iniciado en background",
            resource_id=resource_id
        )

    @strawberry.mutation
    def execute_all_resources(self) -> ExecutionResult:
        """Ejecuta todos los Sources activos en background"""
        def _run_all():
            db = SessionLocal()
            try:
                FetcherManager.run_all(db)
            except Exception:
                pass
            finally:
                db.close()

        threading.Thread(target=_run_all, daemon=True).start()
        return ExecutionResult(success=True, message="Todos los resources activos iniciados en background")

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
    def set_config(self, input: SetConfigInput) -> AppConfigType:
        """Upsert a single application setting."""
        db = get_db()
        try:
            row = db.query(AppConfig).filter(AppConfig.key == input.key).first()
            if row:
                row.value = input.value
                row.updated_at = datetime.utcnow()
            else:
                row = AppConfig(key=input.key, value=input.value, updated_at=datetime.utcnow())
                db.add(row)
            db.commit()
            db.refresh(row)
            return AppConfigType(key=row.key, value=row.value, description=row.description, updated_at=row.updated_at)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation
    def abort_execution(self, id: str) -> ExecutionResult:
        """Mata el thread de una ejecución running y la marca como aborted."""
        with _registry_lock:
            t = _running_threads.get(id)

        if t is None or not t.is_alive():
            # Thread may have finished already — just mark as aborted if still running in DB
            db = get_db()
            try:
                ex = db.query(ResourceExecution).filter(ResourceExecution.id == id).first()
                if ex and ex.status == "running":
                    ex.status = "aborted"
                    ex.completed_at = datetime.utcnow()
                    db.commit()
                    return ExecutionResult(success=True, message="Marked as aborted", resource_id=id)
                return ExecutionResult(success=False, message="Execution not found or not running", resource_id=id)
            finally:
                db.close()

        result = _kill_thread(t)
        if result:
            with _registry_lock:
                _running_threads.pop(id, None)
            # Update DB
            db = get_db()
            try:
                ex = db.query(ResourceExecution).filter(ResourceExecution.id == id).first()
                if ex:
                    ex.status = "aborted"
                    ex.completed_at = datetime.utcnow()
                    db.commit()
            finally:
                db.close()
            return ExecutionResult(success=True, message="Execution aborted", resource_id=id)
        return ExecutionResult(success=False, message="Could not kill thread", resource_id=id)

    @strawberry.mutation
    def delete_execution(self, id: str) -> bool:
        """Soft-delete de una ejecución (la oculta de la vista)"""
        db = get_db()
        try:
            ex = db.query(ResourceExecution).filter(ResourceExecution.id == id).first()
            if not ex:
                raise ValueError(f"Execution '{id}' no encontrada")
            ex.deleted_at = datetime.utcnow()
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
                active=input.active
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

    # ── DerivedDatasetConfig CRUD ─────────────────────────────────────────────

    @strawberry.mutation
    def create_derived_dataset_config(self, input: CreateDerivedDatasetConfigInput) -> DerivedDatasetConfigType:
        """Crea una nueva configuración de dataset derivado"""
        db = get_db()
        try:
            resource = db.query(Resource).filter(Resource.id == input.source_resource_id).first()
            if not resource:
                raise ValueError(f"Resource con id '{input.source_resource_id}' no encontrado")
            cfg = DerivedDatasetConfig(
                id=uuid4(),
                source_resource_id=input.source_resource_id,
                target_name=input.target_name,
                key_field=input.key_field,
                extract_fields=input.extract_fields or [],
                merge_strategy=input.merge_strategy or "upsert",
                enabled=input.enabled,
                description=input.description,
            )
            db.add(cfg)
            db.commit()
            db.refresh(cfg)
            return map_derived_dataset_config(cfg, entry_count=0)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation
    def update_derived_dataset_config(self, id: str, input: UpdateDerivedDatasetConfigInput) -> DerivedDatasetConfigType:
        """Actualiza una configuración de dataset derivado"""
        db = get_db()
        try:
            from app.models import DerivedDatasetEntry
            cfg = db.query(DerivedDatasetConfig).filter(DerivedDatasetConfig.id == id).first()
            if not cfg:
                raise ValueError(f"DerivedDatasetConfig con id '{id}' no encontrado")
            if input.target_name is not None:
                cfg.target_name = input.target_name
            if input.key_field is not None:
                cfg.key_field = input.key_field
            if input.extract_fields is not None:
                cfg.extract_fields = input.extract_fields
            if input.merge_strategy is not None:
                cfg.merge_strategy = input.merge_strategy
            if input.enabled is not None:
                cfg.enabled = input.enabled
            if input.description is not None:
                cfg.description = input.description
            db.commit()
            db.refresh(cfg)
            count = db.query(DerivedDatasetEntry).filter(DerivedDatasetEntry.config_id == cfg.id).count()
            return map_derived_dataset_config(cfg, entry_count=count)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation
    def delete_derived_dataset_config(self, id: str) -> bool:
        """Elimina una configuración de dataset derivado (y todas sus entradas)"""
        db = get_db()
        try:
            cfg = db.query(DerivedDatasetConfig).filter(DerivedDatasetConfig.id == id).first()
            if not cfg:
                raise ValueError(f"DerivedDatasetConfig con id '{id}' no encontrado")
            db.delete(cfg)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation
    def toggle_derived_dataset_config(self, id: str, enabled: bool) -> DerivedDatasetConfigType:
        """Activa o desactiva una configuración de dataset derivado"""
        db = get_db()
        try:
            from app.models import DerivedDatasetEntry
            cfg = db.query(DerivedDatasetConfig).filter(DerivedDatasetConfig.id == id).first()
            if not cfg:
                raise ValueError(f"DerivedDatasetConfig con id '{id}' no encontrado")
            cfg.enabled = enabled
            db.commit()
            db.refresh(cfg)
            count = db.query(DerivedDatasetEntry).filter(DerivedDatasetEntry.config_id == cfg.id).count()
            return map_derived_dataset_config(cfg, entry_count=count)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
