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
from app.models import Resource, ResourceParam, Fetcher, FetcherParams, Application, ResourceExecution, AppConfig, DerivedDatasetConfig, DatasetSubscription, Publisher, ApplicationNotification, Dataset
from datetime import datetime
import os

# Global registry: execution_id (str) → Thread
_running_threads: dict[str, threading.Thread] = {}
_registry_lock = threading.Lock()


class ExecutionAborted(Exception):
    pass


def _append_execution_log(execution_id: str, message: str):
    """Appends a timestamped line to an execution's log file."""
    import os
    log_path = f"data/logs/{execution_id}.log"
    if not os.path.exists(log_path):
        return
    ts = datetime.utcnow().strftime("%H:%M:%S")
    with open(log_path, "a", buffering=1) as f:
        f.write(f"[{ts}] {message}\n")


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
    DatasetSubscriptionType,
    PublisherType,
    CreatePublisherInput,
    UpdatePublisherInput,
    DiscoverSectionInput,
)
from app.graphql_api.queries import map_application, map_resource, map_fetcher, map_type_fetcher_param, map_derived_dataset_config, map_dataset_subscription, map_publisher
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
                description=input.description,
                publisher=input.publisher,
                publisher_id=input.publisher_id or None,
                fetcher_id=input.fetcher_id,
                target_table=input.target_table,
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
            if input.description is not None:
                resource.description = input.description
            if input.publisher_id is not None:
                new_pub_id = input.publisher_id or None
                resource.publisher_id = new_pub_id
                if new_pub_id:
                    pub = db.query(Publisher).filter(Publisher.id == new_pub_id).first()
                    resource.publisher = pub.nombre if pub else resource.publisher
                else:
                    resource.publisher = input.publisher if input.publisher is not None else None
            elif input.publisher is not None:
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
    def clone_resource(self, id: str, name: Optional[str] = None) -> ResourceType:
        """Clona un Resource existente copiando todos sus parámetros.

        El clon se crea inactivo y sin schedule para evitar ejecuciones no deseadas.
        El nombre puede personalizarse; si no se indica se añade ' (copia)'.
        """
        db = get_db()
        try:
            source = db.query(Resource).filter(Resource.id == id).first()
            if not source:
                raise ValueError(f"Resource con id '{id}' no encontrado")

            clone = Resource(
                id=uuid4(),
                name=name or f"{source.name} (copia)",
                description=source.description,
                publisher=source.publisher,
                fetcher_id=source.fetcher_id,
                active=False,
                enable_load=source.enable_load,
                load_mode=source.load_mode,
                schedule=None,
            )
            db.add(clone)
            db.flush()

            for p in db.query(ResourceParam).filter(ResourceParam.resource_id == source.id):
                db.add(ResourceParam(
                    id=uuid4(),
                    resource_id=clone.id,
                    key=p.key,
                    value=p.value,
                    is_external=p.is_external,
                ))

            db.commit()
            db.refresh(clone)
            return map_resource(clone)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation
    def delete_resource(self, id: str, hard_delete: bool = False) -> bool:
        """Elimina una fuente de datos.

        Si hard_delete=False (por defecto): soft-delete — marca deleted_at en el resource
        y en todas sus ejecuciones, conservando el historial en BD.
        Si hard_delete=True: elimina físicamente las ejecuciones y luego el resource.
        """
        db = get_db()
        try:
            resource = db.query(Resource).filter(Resource.id == id).first()
            if not resource:
                raise ValueError(f"Resource con id '{id}' no encontrado")

            now = datetime.utcnow()
            if hard_delete:
                import shutil
                rid = str(resource.id)
                # datasets: borrar ficheros y registros
                datasets = db.query(Dataset).filter(Dataset.resource_id == resource.id).all()
                for ds in datasets:
                    try:
                        if ds.data_path and os.path.exists(ds.data_path):
                            os.remove(ds.data_path)
                    except OSError:
                        pass
                # dataset dirs: borrar directorio completo del resource en datasets/
                dataset_dir = os.path.join("data", "datasets", rid)
                try:
                    if os.path.isdir(dataset_dir):
                        shutil.rmtree(dataset_dir)
                except OSError:
                    pass
                # staging: borrar directorio completo del resource en staging/
                staging_dir = os.path.join("data", "staging", rid)
                try:
                    if os.path.isdir(staging_dir):
                        shutil.rmtree(staging_dir)
                except OSError:
                    pass
                db.query(Dataset).filter(
                    Dataset.resource_id == resource.id
                ).delete(synchronize_session=False)
                db.query(ResourceExecution).filter(
                    ResourceExecution.resource_id == resource.id
                ).delete(synchronize_session=False)
                db.delete(resource)
            else:
                db.query(ResourceExecution).filter(
                    ResourceExecution.resource_id == resource.id,
                    ResourceExecution.deleted_at == None,
                ).update({"deleted_at": now}, synchronize_session=False)
                resource.deleted_at = now

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
            resource_id=resource_id,
            execution_id=execution_id,
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
    def delete_fetcher(self, id: str, hard_delete: bool = False) -> bool:
        """Soft-delete (or hard-delete) de un Fetcher"""
        db = get_db()
        try:
            fetcher = db.query(Fetcher).filter(Fetcher.id == id).first()
            if not fetcher:
                raise ValueError(f"Fetcher with id '{id}' not found")

            active_resources = db.query(Resource).filter(
                Resource.fetcher_id == id, Resource.deleted_at == None
            ).count()
            if active_resources > 0:
                raise ValueError(
                    f"Cannot delete: {active_resources} active resource(s) use this fetcher. "
                    "Delete them first."
                )

            if hard_delete:
                db.query(FetcherParams).filter(FetcherParams.fetcher_id == id).delete()
                db.delete(fetcher)
            else:
                fetcher.deleted_at = datetime.utcnow()
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
                    _append_execution_log(id, "🛑 Execution killed (thread already finished)")
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
                    _append_execution_log(id, "🛑 Execution killed by user")
            finally:
                db.close()
            return ExecutionResult(success=True, message="Execution aborted", resource_id=id)
        return ExecutionResult(success=False, message="Could not kill thread", resource_id=id)

    @strawberry.mutation
    def pause_execution(self, id: str) -> ExecutionResult:
        """Señal cooperativa de pausa: el fetcher terminará la página actual y quedará en estado 'paused'."""
        db = get_db()
        try:
            ex = db.query(ResourceExecution).filter(ResourceExecution.id == id).first()
            if not ex:
                return ExecutionResult(success=False, message="Execution not found", resource_id=id)
            if ex.status != "running":
                return ExecutionResult(success=False, message=f"Execution is '{ex.status}', not running", resource_id=id)
            ex.pause_requested = True
            db.commit()
            _append_execution_log(id, "⏸ Pause requested — will stop at next page boundary")
            return ExecutionResult(success=True, message="Pause signal sent", resource_id=id)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation
    def resume_execution(self, id: str) -> ExecutionResult:
        """Reanuda una ejecución pausada lanzando un nuevo thread desde donde se dejó."""
        db = get_db()
        try:
            ex = db.query(ResourceExecution).filter(ResourceExecution.id == id).first()
            if not ex:
                return ExecutionResult(success=False, message="Execution not found", resource_id=id)
            if ex.status != "paused":
                return ExecutionResult(success=False, message=f"Execution is '{ex.status}', not paused", resource_id=id)
            ex.status = "running"
            ex.pause_requested = False
            db.commit()
            resource_id = str(ex.resource_id)
            execution_id = str(ex.id)
            params = ex.execution_params or {}
            _append_execution_log(execution_id, "▶ Resume requested — restarting thread")
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

        def _run():
            bg_db = SessionLocal()
            try:
                FetcherManager.run(bg_db, resource_id, execution_params=params, execution_id=execution_id)
            except ExecutionAborted:
                try:
                    exc_r = bg_db.query(ResourceExecution).filter(ResourceExecution.id == execution_id).first()
                    if exc_r:
                        exc_r.status = "aborted"
                        exc_r.completed_at = datetime.utcnow()
                        bg_db.commit()
                except Exception:
                    pass
            except Exception as exc:
                try:
                    exc_r = bg_db.query(ResourceExecution).filter(ResourceExecution.id == execution_id).first()
                    if exc_r and exc_r.status == "running":
                        exc_r.status = "failed"
                        exc_r.error_message = str(exc)
                        exc_r.completed_at = datetime.utcnow()
                        bg_db.commit()
                except Exception:
                    pass
            finally:
                bg_db.close()
                with _registry_lock:
                    _running_threads.pop(execution_id, None)

        t = threading.Thread(target=_run, daemon=True, name=f"resume-{execution_id[:8]}")
        t.start()
        with _registry_lock:
            _running_threads[execution_id] = t
        return ExecutionResult(success=True, message="Execution resumed", resource_id=resource_id)

    @strawberry.mutation
    def delete_execution(self, id: str, hard_delete: bool = False) -> bool:
        """Soft-delete (o hard-delete) de una ejecución"""
        db = get_db()
        try:
            ex = db.query(ResourceExecution).filter(ResourceExecution.id == id).first()
            if not ex:
                raise ValueError(f"Execution '{id}' no encontrada")
            if hard_delete:
                db.delete(ex)
            else:
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
                subscribed_projects=input.subscribed_projects,
                active=input.active,
                consumption_mode=input.consumption_mode,
                webhook_url=input.webhook_url,
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
            if input.subscribed_projects is not None:
                application.subscribed_projects = input.subscribed_projects
            if input.active is not None:
                application.active = input.active
            if input.consumption_mode is not None:
                application.consumption_mode = input.consumption_mode
            if input.webhook_url is not None:
                application.webhook_url = input.webhook_url

            db.commit()
            db.refresh(application)
            return map_application(application)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()      

    @strawberry.mutation
    def delete_application(self, id: str, hard_delete: bool = False) -> bool:
        """Soft-delete (or hard-delete) de una Application"""
        db = get_db()
        try:
            application = db.query(Application).filter(Application.id == id).first()
            if not application:
                raise ValueError(f"Application with id '{id}' not found")

            if hard_delete:
                db.query(ApplicationNotification).filter(ApplicationNotification.application_id == id).delete()
                db.query(DatasetSubscription).filter(DatasetSubscription.application_id == id).delete()
                db.delete(application)
            else:
                application.deleted_at = datetime.utcnow()
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
    def delete_derived_dataset_config(self, id: str, hard_delete: bool = False) -> bool:
        """Soft-delete (or hard-delete) de una configuración de dataset derivado"""
        db = get_db()
        try:
            cfg = db.query(DerivedDatasetConfig).filter(DerivedDatasetConfig.id == id).first()
            if not cfg:
                raise ValueError(f"DerivedDatasetConfig with id '{id}' not found")
            if hard_delete:
                db.delete(cfg)  # cascade deletes entries
            else:
                cfg.deleted_at = datetime.utcnow()
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

    @strawberry.mutation
    def subscribe_resource(
        self,
        application_id: str,
        resource_id: str,
        pinned_version: Optional[str] = None,
        auto_upgrade: str = "patch",
    ) -> DatasetSubscriptionType:
        """Suscribe una Application a un Resource para recibir notificaciones de nuevos datasets."""
        db = get_db()
        try:
            if not db.query(Application).filter(Application.id == application_id).first():
                raise ValueError(f"Application '{application_id}' no encontrada")
            if not db.query(Resource).filter(Resource.id == resource_id).first():
                raise ValueError(f"Resource '{resource_id}' no encontrado")
            existing = db.query(DatasetSubscription).filter(
                DatasetSubscription.application_id == application_id,
                DatasetSubscription.resource_id == resource_id,
            ).first()
            if existing:
                raise ValueError("Ya existe una suscripción para esta combinación Application/Resource")
            sub = DatasetSubscription(
                id=uuid4(),
                application_id=application_id,
                resource_id=resource_id,
                pinned_version=pinned_version,
                auto_upgrade=auto_upgrade,
            )
            db.add(sub)
            db.commit()
            db.refresh(sub)
            return map_dataset_subscription(sub)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation
    def unsubscribe_resource(self, id: str) -> bool:
        """Elimina una suscripción por su id."""
        db = get_db()
        try:
            sub = db.query(DatasetSubscription).filter(DatasetSubscription.id == id).first()
            if not sub:
                raise ValueError(f"Suscripción '{id}' no encontrada")
            db.delete(sub)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation
    def create_publisher(self, input: CreatePublisherInput) -> PublisherType:
        """Crea un nuevo Publisher"""
        db = get_db()
        try:
            p = Publisher(
                id=uuid4(),
                nombre=input.nombre,
                acronimo=input.acronimo,
                nivel=input.nivel,
                pais=input.pais,
                comunidad_autonoma=input.comunidad_autonoma,
                provincia=input.provincia,
                municipio=input.municipio,
                portal_url=input.portal_url,
                email=input.email,
                telefono=input.telefono,
            )
            db.add(p)
            db.commit()
            db.refresh(p)
            return map_publisher(p)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation
    def update_publisher(self, id: str, input: UpdatePublisherInput) -> PublisherType:
        """Actualiza un Publisher existente"""
        db = get_db()
        try:
            p = db.query(Publisher).filter(Publisher.id == id).first()
            if not p:
                raise ValueError(f"Publisher '{id}' no encontrado")
            for field in ("nombre", "acronimo", "nivel", "pais", "comunidad_autonoma", "provincia", "municipio", "portal_url", "email", "telefono"):
                val = getattr(input, field, None)
                if val is not None:
                    setattr(p, field, val)
            db.commit()
            db.refresh(p)
            return map_publisher(p)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation
    def delete_publisher(self, id: str, hard_delete: bool = False) -> bool:
        """Soft-delete (or hard-delete) de un Publisher"""
        db = get_db()
        try:
            p = db.query(Publisher).filter(Publisher.id == id).first()
            if not p:
                raise ValueError(f"Publisher '{id}' not found")

            active_resources = db.query(Resource).filter(
                Resource.publisher_id == id, Resource.deleted_at == None
            ).count()
            if active_resources > 0:
                raise ValueError(
                    f"Cannot delete: {active_resources} active resource(s) are linked to this publisher. "
                    "Reassign or delete them first."
                )

            if hard_delete:
                db.delete(p)
            else:
                p.deleted_at = datetime.utcnow()
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    # ── Restore (undo soft-delete) ─────────────────────────────────────────────

    @strawberry.mutation
    def restore_resource(self, id: str) -> bool:
        db = get_db()
        try:
            r = db.query(Resource).filter(Resource.id == id).first()
            if not r:
                raise ValueError(f"Resource '{id}' not found")
            r.deleted_at = None
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation
    def restore_application(self, id: str) -> bool:
        db = get_db()
        try:
            a = db.query(Application).filter(Application.id == id).first()
            if not a:
                raise ValueError(f"Application '{id}' not found")
            a.deleted_at = None
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation
    def restore_publisher(self, id: str) -> bool:
        db = get_db()
        try:
            p = db.query(Publisher).filter(Publisher.id == id).first()
            if not p:
                raise ValueError(f"Publisher '{id}' not found")
            p.deleted_at = None
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation
    def restore_fetcher(self, id: str) -> bool:
        db = get_db()
        try:
            f = db.query(Fetcher).filter(Fetcher.id == id).first()
            if not f:
                raise ValueError(f"Fetcher '{id}' not found")
            f.deleted_at = None
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation
    def restore_execution(self, id: str) -> bool:
        db = get_db()
        try:
            e = db.query(ResourceExecution).filter(ResourceExecution.id == id).first()
            if not e:
                raise ValueError(f"Execution '{id}' not found")
            e.deleted_at = None
            db.commit()
            return True
        except Exception as e2:
            db.rollback()
            raise e2
        finally:
            db.close()

    @strawberry.mutation
    def create_child_resources(
        self,
        parent_resource_id: strawberry.ID,
        sections: List[DiscoverSectionInput],
    ) -> List[ResourceType]:
        """Create child Resources from approved discover sections."""
        import json
        db = get_db()
        try:
            parent = db.query(Resource).filter(Resource.id == parent_resource_id).first()
            if not parent:
                raise ValueError(f"Parent resource not found: {parent_resource_id}")

            # Params to carry over from parent (excluding section-specific ones)
            SKIP_KEYS = {"page_include_patterns", "allowed_extensions"}
            parent_params = [p for p in (parent.params or []) if p.key not in SKIP_KEYS]

            created_ids = []
            for section in sections:
                child = Resource(
                    name=section.name,
                    fetcher_id=parent.fetcher_id,
                    publisher=parent.publisher,
                    publisher_id=parent.publisher_id,
                    target_table=section.target_table,
                    active=True,
                    schedule=section.schedule,
                    parent_resource_id=parent_resource_id,
                    auto_generated=True,
                )
                db.add(child)
                db.flush()

                for pp in parent_params:
                    db.add(ResourceParam(
                        resource_id=child.id,
                        key=pp.key,
                        value=pp.value,
                        is_external=pp.is_external,
                    ))

                if section.page_include_patterns:
                    db.add(ResourceParam(resource_id=child.id, key="page_include_patterns", value=section.page_include_patterns))
                if section.extensions:
                    db.add(ResourceParam(resource_id=child.id, key="allowed_extensions", value=json.dumps(section.extensions)))

                created_ids.append(str(child.id))

            db.commit()

            result = []
            for cid in created_ids:
                child_obj = db.query(Resource).filter(Resource.id == cid).first()
                if child_obj:
                    result.append(map_resource(child_obj))
            return result

        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
