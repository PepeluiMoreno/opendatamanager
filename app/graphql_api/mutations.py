"""
Mutations GraphQL para modificar datos.
"""
import strawberry
from app.rbac import requiere


def _registrar_ui(db, resource, info):
    """Versiona un recurso editado por la UI: bumpea versión, escribe historial
    y marca origin='ui' con el autor de la sesión."""
    from app.services.manifests import registrar_version
    ctx = getattr(info, "context", None)
    usuario = ctx.get("usuario") if isinstance(ctx, dict) else None
    db.flush()
    registrar_version(db, resource, origin="ui", author=getattr(usuario, "username", None))
import threading
import ctypes
from typing import Optional, List, Dict
from uuid import uuid4
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Resource, ResourceCandidate, ResourceParam, Fetcher, FetcherParams, Application, ResourceExecution, AppConfig, DerivedDatasetConfig, ResourceSubscription, Publisher, ApplicationNotification, Dataset, RefrescoExtemporaneo
from sqlalchemy import func
from app.core.huella import huella_params, params_bound
from datetime import datetime
_dt = datetime  # alias usado por varias mutaciones (aprobar/rechazar/revisar)
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
    PresetType,
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
    ResourceSubscriptionType,
    PublisherType,
    CreatePublisherInput,
    UpdatePublisherInput,
    ResourceCandidateType,
    PromoteCandidateInput,
    PromoverRamaInput,
    SolicitudIngresoType,
    CrearSolicitudIngresoInput,
    AprobarSolicitudResult,
    TokenEmitidoResult,
)
from app.graphql_api.queries import (
    map_preset,
    map_application, map_resource, map_fetcher, map_type_fetcher_param,
    map_derived_dataset_config, map_resource_subscription, map_publisher,
    map_resource_candidate,
)
from app.manager.fetcher_manager import FetcherManager
import app.scheduler as scheduler


def get_db():
    """Helper para obtener sesión de BD"""
    db = SessionLocal()
    try:
        return db
    finally:
        pass


def _push_solicitud_resuelta(s, token=None, username=None) -> None:
    """Webhook best-effort de resolución de solicitud. Al aprobar incluye el
    token autogenerado y el username para que el consumidor quede operativo
    sin intervención manual (copiar/pegar)."""
    try:
        url = getattr(s, "callback_url", None)
        if not url:
            return
        from app.services.webhook_push import post_webhook
        payload = {
            "evento": "solicitud_resuelta",
            "solicitudId": str(s.id), "nombre": s.nombre,
            "estado": s.estado, "motivo": s.motivo,
            "resueltaAt": s.resuelta_at.isoformat() if s.resuelta_at else None,
        }
        if token:
            payload["token"] = token
        if username:
            payload["username"] = username
        post_webhook(url, getattr(s, "callback_secret", None), payload)
    except Exception:
        pass


def _aplicacion_de_principal(db, usuario):
    """Application (entidad webhook) vinculada a un principal, casando el slug del
    nombre con el username del principal (app-<slug>)."""
    try:
        from app.models import Application
        from app.service_auth import _slug
        for a in db.query(Application).filter(Application.deleted_at.is_(None)).all():
            if _slug(a.name) == usuario.username:
                return a
    except Exception:
        pass
    return None


def _autorizado_sub(info, db, application_id) -> bool:
    """¿Puede el llamante gestionar suscripciones de `application_id`?
    Sí si tiene 'aplicaciones.gestionar' (admin/gestor) o si es el principal
    'aplicacion' dueño de esa Application (auto-servicio del consumidor)."""
    ctx = info.context if info is not None else None
    permisos = (ctx.get("permisos", set()) if isinstance(ctx, dict)
                else getattr(ctx, "permisos", set())) or set()
    if "aplicaciones.gestionar" in permisos:
        return True
    usuario = None
    if ctx is not None:
        usuario = ctx.get("usuario") if isinstance(ctx, dict) else getattr(ctx, "usuario", None)
    try:
        from app.service_auth import PRINCIPAL_APLICACION
    except Exception:
        PRINCIPAL_APLICACION = "aplicacion"
    if usuario is None or getattr(usuario, "tipo", None) != PRINCIPAL_APLICACION:
        return False
    propia = _aplicacion_de_principal(db, usuario)
    return propia is not None and str(propia.id) == str(application_id)


def _push_token_a_aplicacion(db, usuario, token) -> None:
    """Best-effort: entrega el token recien emitido al webhook de la Application
    vinculada (si tiene url+secret), reutilizando el evento que el consumidor ya
    procesa (solicitud_resuelta/aprobada). Asi emitir/rotar/crear desde la vista
    Applications deja operativo al consumidor sin copiar/pegar."""
    try:
        app = _aplicacion_de_principal(db, usuario)
        if not app or not getattr(app, "webhook_url", None) or not getattr(app, "webhook_secret", None):
            return
        from app.services.webhook_push import post_webhook
        post_webhook(app.webhook_url, app.webhook_secret, {
            "evento": "solicitud_resuelta", "estado": "aprobada",
            "nombre": app.name, "token": token, "username": usuario.username,
        })
    except Exception:
        pass


def _push_recurso_resuelto(db, r) -> None:
    """Webhook best-effort al app que propuso el recurso (resuelto)."""
    try:
        if not getattr(r, "created_by_id", None):
            return
        from app.models import Usuario, Application
        from app.services.webhook_push import post_webhook
        u = db.query(Usuario).filter(Usuario.id == r.created_by_id).first()
        if not u:
            return
        app_row = (db.query(Application).filter(Application.name == u.username).first()
                   or db.query(Application).filter(Application.name.ilike(u.username)).first())
        if not app_row or not app_row.webhook_url:
            return
        post_webhook(app_row.webhook_url, app_row.webhook_secret, {
            "evento": "recurso_resuelto",
            "resourceId": str(r.id), "name": r.name,
            "estadoAprobacion": r.estado_aprobacion, "motivoRechazo": r.motivo_rechazo,
        })
    except Exception:
        pass


@strawberry.type
class Mutation:
    @strawberry.mutation(permission_classes=[requiere("recursos.crear")])
    def create_resource(self, input: CreateResourceInput, info: strawberry.types.Info) -> ResourceType:
        """Crea una nueva fuente de datos"""
        db = get_db()
        try:
            # Verificar que el fetcher existe
            fetcher = db.query(Fetcher).filter(
                Fetcher.id == input.fetcher_id
            ).first()
            if not fetcher:
                raise ValueError(f"Fetcher con id '{input.fetcher_id}' no existe")

            preset_id = None
            if getattr(input, "preset_id", None):
                from app.models import FetcherPreset
                preset = db.query(FetcherPreset).filter(
                    FetcherPreset.id == input.preset_id,
                    FetcherPreset.fetcher_id == fetcher.id,
                    FetcherPreset.deleted_at.is_(None)).first()
                if preset is None:
                    raise ValueError("El perfil (preset) indicado no existe bajo ese fetcher")
                preset_id = preset.id

            # Identidad por contenido (huella de params, ver app/core/huella.py).
            # Si ya existe un recurso no borrado con la misma huella, NO se duplica:
            # se devuelve el existente (el solicitante queda como consumidor; el
            # dueño sigue siendo su creador). Si algún param estático está sin
            # valor (borrador/plantilla), se difiere la huella (NULL, sin dedup).
            pares = [(p.key, p.value) for p in (input.params or [])]
            if params_bound(pares):
                ph = huella_params(pares)
                existente = db.query(Resource).filter(
                    Resource.params_hash == ph,
                    Resource.deleted_at.is_(None),
                ).first()
                if existente:
                    return map_resource(existente)
            else:
                ph = None

            # Crear Resource
            # §11: si quien crea es una aplicación (M2M), el recurso queda
            # 'pendiente' de aprobación; un humano con permiso lo crea 'aprobado'.
            _creador = info.context.get("usuario") if (info and info.context) else None
            _estado = "pendiente" if (_creador is not None and getattr(_creador, "tipo", "humano") == "aplicacion") else "aprobado"
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
                preset_id=preset_id,
                params_hash=ph,
                genera_colecciones=bool(getattr(input, "genera_colecciones", False)),
                estado_aprobacion=_estado,
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

            _registrar_ui(db, resource, info)
            db.commit()
            db.refresh(resource)
            scheduler.sync_schedule(str(resource.id), resource.schedule)
            return map_resource(resource)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation(permission_classes=[requiere("recursos.crear")])
    def import_manifest(self, manifest: strawberry.scalars.JSON) -> strawberry.scalars.JSON:
        """Importa un manifiesto JSON de recursos (idempotente).

        Solo referencia fetchers ya registrados por su `code`; nunca acepta
        class_path ni ids (no inyecta código). Aplica la política de gobernanza si
        está disponible. Queda protegida por la autenticación de /graphql.
        """
        from app.services.manifests import import_manifest as _import_manifest
        db = get_db()
        try:
            return _import_manifest(db, manifest)
        finally:
            db.close()

    @strawberry.mutation(permission_classes=[requiere("recursos.editar")])
    def update_resource(self, id: str, input: UpdateResourceInput, info: strawberry.types.Info) -> ResourceType:
        """Actualiza una fuente de datos existente"""
        db = get_db()
        try:
            resource = db.query(Resource).filter(Resource.id == id).first()
            if not resource:
                raise ValueError(f"Resource con id '{id}' no encontrado")

            from app.services.integrity import guard_resource_update
            guard_resource_update(db, resource, input)

            # Autoridad del schedule: solo el creador (created_by_id) puede cambiar
            # la cadencia de refresco. Los consumidores usan la cadencia establecida
            # o piden un refresco a demanda (que consume su cuota).
            usuario = info.context.get("usuario") if (info and info.context) else None
            if input.schedule is not None and (input.schedule or None) != resource.schedule:
                if resource.created_by_id is not None and (usuario is None or usuario.id != resource.created_by_id):
                    raise ValueError(
                        "Solo el creador del recurso puede cambiar su schedule de refresco. "
                        "Los consumidores usan la cadencia establecida o piden un refresco a demanda (con cuota)."
                    )

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
            if getattr(input, "preset_id", None) is not None:
                if input.preset_id == "":
                    resource.preset_id = None
                else:
                    from app.models import FetcherPreset
                    preset = db.query(FetcherPreset).filter(
                        FetcherPreset.id == input.preset_id,
                        FetcherPreset.fetcher_id == resource.fetcher_id,
                        FetcherPreset.deleted_at.is_(None)).first()
                    if preset is None:
                        raise ValueError("El perfil (preset) indicado no existe bajo ese fetcher")
                    resource.preset_id = preset.id
            if input.active is not None:
                resource.active = input.active
            if getattr(input, "genera_colecciones", None) is not None:
                resource.genera_colecciones = bool(input.genera_colecciones)
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

                # Recalcular la huella de identidad (solo si los params están
                # acotados) y rechazar si colisiona con otro recurso no borrado.
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
                    resource.params_hash = None

            _registrar_ui(db, resource, info)
            db.commit()
            db.refresh(resource)
            scheduler.sync_schedule(str(resource.id), resource.schedule)
            return map_resource(resource)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation(permission_classes=[requiere("recursos.crear")])
    def clone_resource(self, id: str, info: strawberry.types.Info, name: Optional[str] = None) -> ResourceType:
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
                preset_id=source.preset_id,
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

            _registrar_ui(db, clone, info)
            db.commit()
            db.refresh(clone)
            return map_resource(clone)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation(permission_classes=[requiere("recursos.borrar")])
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
            from app.services.integrity import guard_resource_delete
            guard_resource_delete(db, resource)
            children = db.query(Resource).filter(
                Resource.parent_resource_id == resource.id,
                Resource.auto_generated == True,
            ).all()
            if hard_delete:
                import shutil
                def _hard_delete_one(res):
                    rid = str(res.id)
                    datasets = db.query(Dataset).filter(Dataset.resource_id == res.id).all()
                    for ds in datasets:
                        try:
                            if ds.data_path and os.path.exists(ds.data_path):
                                os.remove(ds.data_path)
                        except OSError:
                            pass
                    for d in ["datasets", "staging"]:
                        p = os.path.join("data", d, rid)
                        try:
                            if os.path.isdir(p):
                                shutil.rmtree(p)
                        except OSError:
                            pass
                    db.query(Dataset).filter(Dataset.resource_id == res.id).delete(synchronize_session=False)
                    db.query(ResourceExecution).filter(ResourceExecution.resource_id == res.id).delete(synchronize_session=False)
                    db.delete(res)

                for child in children:
                    _hard_delete_one(child)
                _hard_delete_one(resource)
            else:
                all_ids = [resource.id] + [c.id for c in children]
                db.query(ResourceExecution).filter(
                    ResourceExecution.resource_id.in_(all_ids),
                    ResourceExecution.deleted_at == None,
                ).update({"deleted_at": now}, synchronize_session=False)
                for child in children:
                    child.deleted_at = now
                resource.deleted_at = now

            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation(permission_classes=[requiere("ejecuciones.lanzar")])
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
                return ExecutionResult(success=False, message=f"Resource con id '{id}' no encontrado")
            if getattr(resource, "estado_aprobacion", "aprobado") != "aprobado":
                return ExecutionResult(
                    success=False,
                    message=f"El recurso no está aprobado (estado={resource.estado_aprobacion}); no puede ejecutarse.",
                    resource_id=str(resource.id),
                )
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

            # Cooldown anti-abuso: si el recurso ya se ejecutó CON ÉXITO hace poco,
            # se rechaza el refresco (configurable; 0 desactiva).
            cd_cfg = db.query(AppConfig).filter(AppConfig.key == "execute_cooldown_minutes").first()
            cooldown_min = int(cd_cfg.value) if cd_cfg else 60
            if cooldown_min > 0:
                from datetime import timedelta
                umbral = datetime.utcnow() - timedelta(minutes=cooldown_min)
                reciente = (
                    db.query(ResourceExecution)
                    .filter(
                        ResourceExecution.resource_id == resource.id,
                        ResourceExecution.status == "completed",
                        ResourceExecution.completed_at != None,
                        ResourceExecution.completed_at >= umbral,
                        ResourceExecution.deleted_at == None,
                    )
                    .order_by(ResourceExecution.completed_at.desc())
                    .first()
                )
                if reciente:
                    mins = int((datetime.utcnow() - reciente.completed_at).total_seconds() // 60)
                    return ExecutionResult(
                        success=False,
                        message=(f"Cooldown: este recurso se ejecutó con éxito hace {mins} min. "
                                 f"Se admite un refresco cada {cooldown_min} min (ajustable en "
                                 f"AppConfig execute_cooldown_minutes)."),
                        resource_id=resource_id,
                    )

            # Cuota diaria de refrescos a demanda. Los refrescos PROGRAMADOS
            # (scheduler -> FetcherManager) no pasan por aquí y no consumen cuota.
            usuario = info.context.get("usuario") if (info and info.context) else None
            if usuario is None:
                return ExecutionResult(success=False, resource_id=resource_id,
                    message="El refresco a demanda requiere un principal autenticado.")
            limite = getattr(usuario, "cuota_refrescos_diaria", 0) or 0
            inicio_dia = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            usados = db.query(func.count(RefrescoExtemporaneo.id)).filter(
                RefrescoExtemporaneo.created_by_id == usuario.id,
                RefrescoExtemporaneo.created_at >= inicio_dia,
            ).scalar() or 0
            if usados >= limite:
                return ExecutionResult(success=False, resource_id=resource_id,
                    message=(f"Cuota diaria de refrescos a demanda agotada ({usados}/{limite}). "
                             "El recurso se refresca según su schedule; reintenta mañana o solicita más cuota."))
            db.add(RefrescoExtemporaneo(resource_id=resource.id, created_by_id=usuario.id))
            db.commit()
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

    @strawberry.mutation(permission_classes=[requiere("ejecuciones.lanzar")])
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

    @strawberry.mutation(permission_classes=[requiere("fetchers.gestionar")])
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

    @strawberry.mutation(permission_classes=[requiere("fetchers.gestionar")])
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

    @strawberry.mutation(permission_classes=[requiere("fetchers.gestionar")])
    def create_fetcher_preset(self, fetcher_id: str, code: str,
                              description: Optional[str] = None,
                              params: Optional[strawberry.scalars.JSON] = None,
                              locked_params: Optional[strawberry.scalars.JSON] = None) -> PresetType:
        """Crea un perfil (preset) bajo una especie: particularización con nombre."""
        from app.models import FetcherPreset
        db = get_db()
        try:
            fetcher = db.query(Fetcher).filter(Fetcher.id == fetcher_id,
                                               Fetcher.deleted_at.is_(None)).first()
            if not fetcher:
                raise ValueError("La especie indicada no existe")
            code = (code or "").strip()
            if not code:
                raise ValueError("El perfil necesita un código")
            dup = db.query(FetcherPreset).filter(
                FetcherPreset.fetcher_id == fetcher.id,
                FetcherPreset.code == code,
                FetcherPreset.deleted_at.is_(None)).first()
            if dup:
                raise ValueError(f"Ya existe el perfil '{code}' bajo '{fetcher.code}'")
            preset = FetcherPreset(fetcher_id=fetcher.id, code=code,
                                   description=description, params=params or {},
                                   locked_params=[k for k in (locked_params or []) if k in (params or {})])
            db.add(preset)
            db.commit()
            db.refresh(preset)
            return map_preset(preset)
        finally:
            db.close()

    @strawberry.mutation(permission_classes=[requiere("fetchers.gestionar")])
    def update_fetcher_preset(self, id: str, code: Optional[str] = None,
                              description: Optional[str] = None,
                              params: Optional[strawberry.scalars.JSON] = None,
                              locked_params: Optional[strawberry.scalars.JSON] = None) -> PresetType:
        """Actualiza un perfil. Los recursos que lo usan heredan el cambio en su
        próxima ejecución (salvo en los campos que hayan sobrescrito)."""
        from app.models import FetcherPreset
        db = get_db()
        try:
            preset = db.query(FetcherPreset).filter(FetcherPreset.id == id,
                                                    FetcherPreset.deleted_at.is_(None)).first()
            if not preset:
                raise ValueError("El perfil no existe")
            from app.services.integrity import guard_preset_update
            guard_preset_update(db, preset, changing_contract=(params is not None and params != preset.params))
            if code is not None and code.strip() and code.strip() != preset.code:
                dup = db.query(FetcherPreset).filter(
                    FetcherPreset.fetcher_id == preset.fetcher_id,
                    FetcherPreset.code == code.strip(),
                    FetcherPreset.deleted_at.is_(None),
                    FetcherPreset.id != preset.id).first()
                if dup:
                    raise ValueError(f"Ya existe el perfil '{code.strip()}' bajo esta especie")
                preset.code = code.strip()
            if description is not None:
                preset.description = description
            if params is not None:
                preset.params = params
            if locked_params is not None:
                # el candado solo tiene sentido sobre valores que la variante fija
                preset.locked_params = [k for k in locked_params if k in (preset.params or {})]
            db.commit()
            db.refresh(preset)
            return map_preset(preset)
        finally:
            db.close()

    @strawberry.mutation(permission_classes=[requiere("fetchers.gestionar")])
    def delete_fetcher_preset(self, id: str) -> bool:
        """Retira (soft-delete) un perfil. Bloqueado si algún recurso vivo lo usa."""
        from app.models import FetcherPreset
        db = get_db()
        try:
            preset = db.query(FetcherPreset).filter(FetcherPreset.id == id,
                                                    FetcherPreset.deleted_at.is_(None)).first()
            if not preset:
                raise ValueError("El perfil no existe")
            en_uso = db.query(Resource).filter(Resource.preset_id == preset.id,
                                               Resource.deleted_at.is_(None)).count()
            if en_uso:
                raise ValueError(
                    f"El perfil '{preset.code}' está en uso por {en_uso} recurso(s); "
                    "reasígnalos antes de retirarlo")
            preset.deleted_at = datetime.utcnow()
            db.commit()
            return True
        finally:
            db.close()

    @strawberry.mutation(permission_classes=[requiere("fetchers.gestionar")])
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

    @strawberry.mutation(permission_classes=[requiere("fetchers.gestionar")])
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
                hint=input.hint,
                help_md=input.help_md,
                visible_when=input.visible_when,
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

    @strawberry.mutation(permission_classes=[requiere("fetchers.gestionar")])
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
            if input.hint is not None:
                param.hint = input.hint
            if input.help_md is not None:
                param.help_md = input.help_md
            if input.visible_when is not None:
                param.visible_when = input.visible_when

            db.commit()
            db.refresh(param)
            return map_type_fetcher_param(param)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation(permission_classes=[requiere("fetchers.gestionar")])
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

    @strawberry.mutation(permission_classes=[requiere("settings.gestionar")])
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

    @strawberry.mutation(permission_classes=[requiere("ejecuciones.parar")])
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

    @strawberry.mutation(permission_classes=[requiere("ejecuciones.parar")])
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

    @strawberry.mutation(permission_classes=[requiere("ejecuciones.lanzar")])
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

    @strawberry.mutation(permission_classes=[requiere("ejecuciones.parar")])
    def delete_execution(self, id: str, hard_delete: bool = False) -> bool:
        """Soft-delete (o hard-delete) de una ejecución"""
        db = get_db()
        try:
            ex = db.query(ResourceExecution).filter(ResourceExecution.id == id).first()
            if not ex:
                raise ValueError(f"Execution '{id}' no encontrada")
            if hard_delete:
                # Dataset.execution_id no tiene ondelete=SET NULL — nulificarlo aquí
                # para que la FK no bloquee el delete cuando hay datasets producidos.
                from app.models import Dataset
                db.query(Dataset).filter(Dataset.execution_id == ex.id).update(
                    {Dataset.execution_id: None}, synchronize_session=False
                )
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

    @strawberry.mutation(permission_classes=[requiere("aplicaciones.gestionar")])
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
                persona_contacto=getattr(input, "persona_contacto", None),
                email=getattr(input, "email", None),
                telefono=getattr(input, "telefono", None),
                github_url=getattr(input, "github_url", None),
                proposito=getattr(input, "proposito", None),
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

    @strawberry.mutation(permission_classes=[requiere("aplicaciones.gestionar")])
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
            for _f in ("persona_contacto", "email", "telefono", "github_url", "proposito"):
                _v = getattr(input, _f, None)
                if _v is not None:
                    setattr(application, _f, _v)

            db.commit()
            db.refresh(application)
            return map_application(application)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()      

    @strawberry.mutation(permission_classes=[requiere("aplicaciones.gestionar")])
    def delete_application(self, id: str, hard_delete: bool = False) -> bool:
        """Ruta ÚNICA de borrado. Elimina la aplicación por completo: borra la
        Application (webhook) y su principal+tokens, desvincula recursos (que
        pasan a 'sistema'), anula sus solicitudes y avisa al consumidor
        (estado=anulada) para que deje de estar operativo y vuelva al alta."""
        from app.models import (Usuario, Resource, ServiceToken, SolicitudIngreso,
                                 ResourceSubscription, ApplicationNotification)
        from app.service_auth import PRINCIPAL_APLICACION, _slug
        db = get_db()
        try:
            application = db.query(Application).filter(Application.id == id).first()
            if not application:
                raise ValueError(f"Application with id '{id}' not found")
            _wh_url = getattr(application, "webhook_url", None)
            _wh_secret = getattr(application, "webhook_secret", None)
            _name = application.name

            # Principal vinculado (app-<slug>): su acceso muere con la aplicación.
            u = db.query(Usuario).filter(
                Usuario.username == _slug(_name),
                Usuario.tipo == PRINCIPAL_APLICACION).first()
            sols = []
            if u is not None:
                sols = db.query(SolicitudIngreso).filter(
                    SolicitudIngreso.usuario_id == u.id).all()
                for s in sols:
                    s.estado = "anulada"
                    s.motivo = "Aplicación eliminada en ODM"
                    s.resuelta_at = _dt.utcnow()
                db.query(Resource).filter(
                    Resource.created_by_id == u.id).update(
                    {"auto_generated": True}, synchronize_session=False)
                db.query(ServiceToken).filter(
                    ServiceToken.usuario_id == u.id).delete(synchronize_session=False)

            db.query(ApplicationNotification).filter(
                ApplicationNotification.application_id == id).delete(synchronize_session=False)
            db.query(ResourceSubscription).filter(
                ResourceSubscription.application_id == id).delete(synchronize_session=False)
            if hard_delete:
                db.delete(application)
            else:
                application.deleted_at = _dt.utcnow()
                application.active = False
                application.created_by_id = None
                application.name = f"{_name}__del_{int(_dt.utcnow().timestamp())}"
            if u is not None:
                db.delete(u)
            db.commit()

            # Aviso de des-registro al consumidor (best-effort).
            try:
                from app.services.webhook_push import post_webhook
                if _wh_url and _wh_secret:
                    post_webhook(_wh_url, _wh_secret, {
                        "evento": "solicitud_resuelta", "estado": "anulada", "nombre": _name})
            except Exception:
                pass
            for s in sols:
                _push_solicitud_resuelta(s)
            return True
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation(permission_classes=[requiere("aplicaciones.gestionar")])
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

    @strawberry.mutation(permission_classes=[requiere("aplicaciones.gestionar")])
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

    @strawberry.mutation(permission_classes=[requiere("aplicaciones.gestionar")])
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

    @strawberry.mutation(permission_classes=[requiere("programacion.gestionar")])
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

    @strawberry.mutation(permission_classes=[requiere("programacion.gestionar")])
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

    @strawberry.mutation(permission_classes=[requiere("programacion.gestionar")])
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

    @strawberry.mutation(permission_classes=[requiere("programacion.gestionar")])
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
        info: strawberry.types.Info,
        pinned_version: Optional[str] = None,
        auto_upgrade: str = "patch",
    ) -> ResourceSubscriptionType:
        """Suscribe una Application a un Resource. Permitido al admin
        (aplicaciones.gestionar) o al propio principal dueño de la Application."""
        db = get_db()
        try:
            if not _autorizado_sub(info, db, application_id):
                raise PermissionError("No autorizado para suscribir esta aplicación")
            if not db.query(Application).filter(Application.id == application_id).first():
                raise ValueError(f"Application '{application_id}' no encontrada")
            if not db.query(Resource).filter(Resource.id == resource_id).first():
                raise ValueError(f"Resource '{resource_id}' no encontrado")
            existing = db.query(ResourceSubscription).filter(
                ResourceSubscription.application_id == application_id,
                ResourceSubscription.resource_id == resource_id,
            ).first()
            if existing:
                raise ValueError("Ya existe una suscripción para esta combinación Application/Resource")
            sub = ResourceSubscription(
                id=uuid4(),
                application_id=application_id,
                resource_id=resource_id,
                pinned_version=pinned_version,
                auto_upgrade=auto_upgrade,
            )
            db.add(sub)
            db.commit()
            db.refresh(sub)
            return map_resource_subscription(sub)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation
    def unsubscribe_resource(self, id: str, info: strawberry.types.Info) -> bool:
        """Elimina una suscripción. Permitido al admin (aplicaciones.gestionar)
        o al propio principal dueño de la Application de la suscripción."""
        db = get_db()
        try:
            sub = db.query(ResourceSubscription).filter(ResourceSubscription.id == id).first()
            if not sub:
                raise ValueError(f"Suscripción '{id}' no encontrada")
            if not _autorizado_sub(info, db, sub.application_id):
                raise PermissionError("No autorizado para gestionar esta suscripción")
            db.delete(sub)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation(permission_classes=[requiere("publishers.gestionar")])
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

    @strawberry.mutation(permission_classes=[requiere("publishers.gestionar")])
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

    @strawberry.mutation(permission_classes=[requiere("publishers.gestionar")])
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

    @strawberry.mutation(permission_classes=[requiere("recursos.borrar")])
    def restore_resource(self, id: str) -> bool:
        db = get_db()
        try:
            r = db.query(Resource).filter(Resource.id == id).first()
            if not r:
                raise ValueError(f"Resource '{id}' not found")
            r.deleted_at = None
            db.query(Resource).filter(
                Resource.parent_resource_id == r.id,
                Resource.auto_generated == True,
            ).update({"deleted_at": None}, synchronize_session=False)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation(permission_classes=[requiere("aplicaciones.gestionar")])
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

    @strawberry.mutation(permission_classes=[requiere("publishers.gestionar")])
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

    @strawberry.mutation(permission_classes=[requiere("fetchers.gestionar")])
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

    @strawberry.mutation(permission_classes=[requiere("ejecuciones.lanzar")])
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

    @strawberry.mutation(permission_classes=[requiere("recursos.crear")])
    def promote_candidate(
        self,
        id: strawberry.ID,
        input: PromoteCandidateInput,
    ) -> ResourceType:
        """Promueve una `ResourceCandidate` a Resource hijo (auto_generated).

        El hijo hereda fetcher y `root_url` del crawler padre. `matched_urls` y
        `dimensions` se leen de la fila ResourceCandidate en cada ejecución."""
        from datetime import datetime as _dt
        db = get_db()
        try:
            candidate = db.query(ResourceCandidate).filter(ResourceCandidate.id == id).first()
            if not candidate:
                raise ValueError(f"Candidato no encontrado: {id}")
            if candidate.status not in ("discovered", "reviewed"):
                raise ValueError(f"Candidato en estado '{candidate.status}' no es promovible")

            parent = db.query(Resource).filter(Resource.id == candidate.crawler_resource_id).first()
            if not parent:
                raise ValueError(f"Crawler padre no encontrado: {candidate.crawler_resource_id}")

            # Variante opcional: resuelta por `code` bajo la especie del padre.
            preset_id = None
            if input.variant:
                from app.models import FetcherPreset
                preset = db.query(FetcherPreset).filter(
                    FetcherPreset.code == input.variant,
                    FetcherPreset.fetcher_id == parent.fetcher_id,
                    FetcherPreset.deleted_at.is_(None)).first()
                if not preset:
                    raise ValueError(
                        f"Variante '{input.variant}' no existe para la especie del crawler")
                preset_id = preset.id

            child = Resource(
                name=input.name,
                fetcher_id=parent.fetcher_id,
                publisher=parent.publisher,
                publisher_id=parent.publisher_id,
                target_table=input.target_table,
                active=True,
                schedule=input.schedule,
                enable_load=bool(input.enable_load),
                load_mode=input.load_mode or "upsert",
                parent_resource_id=parent.id,
                auto_generated=True,
                preset_id=preset_id,
            )
            db.add(child)
            db.flush()

            # El hijo hereda únicamente `root_url` del padre — todos los demás
            # params son defaults internos del WebTreeFetcher.
            root_url = next((p.value for p in (parent.params or []) if p.key == "root_url"), None)
            if root_url:
                db.add(ResourceParam(resource_id=child.id, key="root_url", value=root_url))

            candidate.status = "promoted"
            candidate.promoted_resource_id = child.id
            candidate.reviewed_at = _dt.utcnow()
            db.commit()

            child_obj = db.query(Resource).filter(Resource.id == child.id).first()
            return map_resource(child_obj)

        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation(permission_classes=[requiere("recursos.crear")])
    def promover_rama(self, input: PromoverRamaInput) -> List[ResourceType]:
        """Promueve una rama del árbol del crawler: funde sus hojas en recurso(s),
        derivando como columnas los segmentos que varían. Por defecto solo las
        fusiones con patrón de serie ({*}); las hojas sueltas se omiten salvo
        `incluirNoSeries`. Generaliza promote_candidate a una rama entera.

        Por cada fusión crea un ResourceCandidate generalizado (status promoted)
        que alimentará al hijo en ejecución, y deja las hojas fuente en `merged`."""
        from app.services.taxonomia import segmentos_constantes, fundir_rama
        from datetime import datetime as _dt
        db = get_db()
        try:
            parent = db.query(Resource).filter(Resource.id == input.crawler_resource_id).first()
            if not parent:
                raise ValueError("Crawler no encontrado")
            rama_segs = segmentos_constantes(input.rama_path)
            if not rama_segs:
                raise ValueError("ramaPath vacío")

            cands = (
                db.query(ResourceCandidate)
                .filter(
                    ResourceCandidate.crawler_resource_id == parent.id,
                    ResourceCandidate.deleted_at.is_(None),
                    ResourceCandidate.status.in_(["discovered", "reviewed"]),
                )
                .all()
            )
            bajo = [c for c in cands
                    if segmentos_constantes(c.path_template)[:len(rama_segs)] == rama_segs]
            if not bajo:
                raise ValueError("La rama no tiene candidatos promovibles")

            items = [{
                "id": str(c.id), "path_template": c.path_template,
                "matched_urls": c.matched_urls, "file_types": c.file_types,
                "dimensions": c.dimensions,
            } for c in bajo]
            fusiones = fundir_rama(items)
            if not input.incluir_no_series:
                fusiones = [f for f in fusiones if f["path_template"].rstrip("/").endswith("{*}")]
            if not fusiones:
                raise ValueError("No hay series promovibles en la rama (usa incluirNoSeries para las hojas sueltas)")

            preset_id = None
            if input.variant:
                from app.models import FetcherPreset
                preset = db.query(FetcherPreset).filter(
                    FetcherPreset.code == input.variant,
                    FetcherPreset.fetcher_id == parent.fetcher_id,
                    FetcherPreset.deleted_at.is_(None)).first()
                if not preset:
                    raise ValueError(f"Variante '{input.variant}' no existe para la especie del crawler")
                preset_id = preset.id

            root_url = next((p.value for p in (parent.params or []) if p.key == "root_url"), None)
            base = input.name or rama_segs[-1]
            by_id = {str(c.id): c for c in bajo}

            creados = []
            for idx, f in enumerate(fusiones):
                sufijo = "" if len(fusiones) == 1 else f" #{idx + 1}"
                nombre = f"{base}{sufijo}"
                if db.query(Resource).filter(Resource.name == nombre).first():
                    nombre = f"{nombre} [{str(parent.id)[:6]}]"

                fundido = ResourceCandidate(
                    crawler_resource_id=parent.id,
                    path_template=f["path_template"],
                    dimensions=f["dimensions"],
                    matched_urls=f["matched_urls"],
                    file_types=f["file_types"],
                    suggested_name=nombre,
                    confidence=1.0,
                    status="promoted",
                )
                db.add(fundido)
                db.flush()

                child = Resource(
                    name=nombre,
                    fetcher_id=parent.fetcher_id,
                    publisher=parent.publisher,
                    publisher_id=parent.publisher_id,
                    active=True,
                    schedule=input.schedule,
                    enable_load=bool(input.enable_load),
                    parent_resource_id=parent.id,
                    auto_generated=True,
                    preset_id=preset_id,
                )
                db.add(child)
                db.flush()
                if root_url:
                    db.add(ResourceParam(resource_id=child.id, key="root_url", value=root_url))

                fundido.promoted_resource_id = child.id
                for cid in f["candidato_ids"]:
                    src = by_id.get(str(cid))
                    if src:
                        src.status = "merged"
                        src.merged_into_id = fundido.id
                        src.reviewed_at = _dt.utcnow()
                creados.append(child.id)

            db.commit()
            objs = db.query(Resource).filter(Resource.id.in_(creados)).all()
            return [map_resource(o) for o in objs]
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation(permission_classes=[requiere("recursos.crear")])
    def discard_candidate(self, id: strawberry.ID, reviewer: Optional[str] = None) -> ResourceCandidateType:
        """Marca una candidata como `discarded`."""
        from datetime import datetime as _dt
        db = get_db()
        try:
            c = db.query(ResourceCandidate).filter(ResourceCandidate.id == id).first()
            if not c:
                raise ValueError(f"Candidato no encontrado: {id}")
            c.status = "discarded"
            c.reviewed_at = _dt.utcnow()
            if reviewer:
                c.reviewed_by = reviewer
            db.commit()
            return map_resource_candidate(c)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation(permission_classes=[requiere("recursos.crear")])
    def merge_candidates(
        self,
        source_ids: List[strawberry.ID],
        target_id: strawberry.ID,
    ) -> ResourceCandidateType:
        """Funde varias candidatas en una. Las `source_ids` quedan en `merged` y
        sus `matched_urls` se acumulan en la `target_id`."""
        from datetime import datetime as _dt
        db = get_db()
        try:
            target = db.query(ResourceCandidate).filter(ResourceCandidate.id == target_id).first()
            if not target:
                raise ValueError(f"Candidato target no encontrado: {target_id}")
            merged_urls = list(target.matched_urls or [])
            merged_ft: Dict = dict(target.file_types or {})
            for sid in source_ids:
                if str(sid) == str(target_id):
                    continue
                src = db.query(ResourceCandidate).filter(ResourceCandidate.id == sid).first()
                if not src:
                    continue
                for u in (src.matched_urls or []):
                    if u not in merged_urls:
                        merged_urls.append(u)
                for ft, n in (src.file_types or {}).items():
                    merged_ft[ft] = merged_ft.get(ft, 0) + int(n)
                src.status = "merged"
                src.merged_into_id = target.id
                src.reviewed_at = _dt.utcnow()
            target.matched_urls = merged_urls
            target.file_types = merged_ft
            target.reviewed_at = _dt.utcnow()
            db.commit()
            return map_resource_candidate(target)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @strawberry.mutation(permission_classes=[requiere("recursos.crear")])
    def split_candidate(
        self,
        id: strawberry.ID,
        groups: strawberry.scalars.JSON,
    ) -> List[ResourceCandidateType]:
        """Parte una candidata en N candidatas hijas. `groups` es una lista de
        `{name, urls}` — cada grupo nace como nueva candidata `discovered` con
        `split_from_id` apuntando a la original. La original pasa a `split`."""
        from datetime import datetime as _dt
        db = get_db()
        try:
            src = db.query(ResourceCandidate).filter(ResourceCandidate.id == id).first()
            if not src:
                raise ValueError(f"Candidato no encontrado: {id}")
            new_ids = []
            for g in (groups or []):
                urls = list(g.get("urls") or [])
                if not urls:
                    continue
                child = ResourceCandidate(
                    execution_id=src.execution_id,
                    crawler_resource_id=src.crawler_resource_id,
                    path_template=src.path_template,
                    dimensions=src.dimensions or [],
                    matched_urls=urls,
                    file_types={},
                    suggested_name=g.get("name") or src.suggested_name,
                    confidence=src.confidence,
                    status="discovered",
                    split_from_id=src.id,
                )
                db.add(child)
                db.flush()
                new_ids.append(child.id)
            src.status = "split"
            src.reviewed_at = _dt.utcnow()
            db.commit()
            result = db.query(ResourceCandidate).filter(ResourceCandidate.id.in_(new_ids)).all()
            return [map_resource_candidate(c) for c in result]
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    # ── §12 Alta de aplicaciones (M2M) ─────────────────────────────────────

    @strawberry.mutation
    def crear_solicitud_ingreso(self, input: CrearSolicitudIngresoInput,
                                info: strawberry.types.Info) -> SolicitudIngresoType:
        """Self-service: registra una solicitud de alta de aplicación. No crea
        nada operativo; queda 'pendiente' hasta que un admin la apruebe."""
        from app.models import SolicitudIngreso
        # Validación de requeridos (rechaza solicitudes incompletas, también por API).
        _req = {"nombre": input.nombre, "descripcion": getattr(input, "descripcion", None),
                "persona_contacto": getattr(input, "persona_contacto", None),
                "email": getattr(input, "email", None), "github_url": getattr(input, "github_url", None)}
        _faltan = [k for k, v in _req.items() if not (v or "").strip()]
        if _faltan:
            raise ValueError("Faltan campos obligatorios: " + ", ".join(_faltan))
        db = get_db()
        try:
            # Identidad: si ya hay una Application activa con este nombre, el secreto
            # de webhook debe coincidir (mismo consumidor re-llaveando tras perder el
            # token). Si no coincide, es otro reclamando el nombre -> rechazar.
            from app.models import Application as _App
            _app_exist = db.query(_App).filter(
                _App.name == input.nombre, _App.deleted_at.is_(None)).first()
            if _app_exist is not None and getattr(_app_exist, "webhook_secret", None):
                if (getattr(input, "callback_secret", None) or "") != (_app_exist.webhook_secret or ""):
                    raise ValueError(
                        "Ya existe una aplicación registrada con este nombre. Si es tuya, "
                        "usa el mismo secreto de webhook; si no, elige otro nombre.")
            # §9 anti-duplicados: si ya hay una pendiente con el mismo nombre, se
            # devuelve esa (idempotente) en vez de crear otra.
            existente = db.query(SolicitudIngreso).filter(
                SolicitudIngreso.nombre == input.nombre,
                SolicitudIngreso.estado == "pendiente",
            ).first()
            if existente is not None:
                s = existente
                # Sana una pendiente anterior creada sin callback (p. ej. antes de
                # configurar la URL pública del consumidor): completa callback_url/secret.
                _cu = getattr(input, "callback_url", None)
                _cs = getattr(input, "callback_secret", None)
                _ch = False
                if _cu and not getattr(s, "callback_url", None):
                    s.callback_url = _cu; _ch = True
                if _cs and not getattr(s, "callback_secret", None):
                    s.callback_secret = _cs; _ch = True
                if _ch:
                    db.commit()
            else:
                s = SolicitudIngreso(
                    nombre=input.nombre,
                    consumption_mode=getattr(input, "consumption_mode", None),
                    contacto=getattr(input, "contacto", None),
                    proposito=getattr(input, "proposito", None),
                    descripcion=getattr(input, "descripcion", None),
                    persona_contacto=getattr(input, "persona_contacto", None),
                    email=getattr(input, "email", None),
                    telefono=getattr(input, "telefono", None),
                    github_url=getattr(input, "github_url", None),
                    estado="pendiente",
                    callback_url=getattr(input, "callback_url", None),
                    callback_secret=getattr(input, "callback_secret", None),
                )
                db.add(s)
                db.commit()
            return SolicitudIngresoType(
                id=str(s.id), nombre=s.nombre, contacto=s.contacto, proposito=s.proposito,
                descripcion=s.descripcion, persona_contacto=s.persona_contacto, email=s.email,
                telefono=s.telefono, github_url=s.github_url,
                estado=s.estado, motivo=s.motivo, created_at=getattr(s, "created_at", None),
                resuelta_at=s.resuelta_at, usuario_id=None,
            )
        except Exception:
            db.rollback(); raise
        finally:
            db.close()

    @strawberry.mutation(permission_classes=[requiere("aplicaciones.aprobar")])
    def aprobar_solicitud_ingreso(self, id: strawberry.ID,
                                  info: strawberry.types.Info) -> AprobarSolicitudResult:
        """Aprueba una solicitud: materializa el principal 'aplicacion' (Usuario
        tipo='aplicacion' con rol suscriptor) y emite su primer token Bearer.
        El token en claro se devuelve UNA sola vez."""
        from app.models import SolicitudIngreso
        from app.service_auth import crear_principal_aplicacion, emitir_token
        db = get_db()
        try:
            s = db.query(SolicitudIngreso).filter(SolicitudIngreso.id == id).first()
            if not s:
                raise ValueError("Solicitud no encontrada")
            if s.estado != "pendiente":
                raise ValueError(f"La solicitud ya está '{s.estado}'")
            from app.models import ServiceToken
            usuario = crear_principal_aplicacion(db, s.nombre, s.contacto)
            # token único: borra cualquier token previo de esta app y emite uno nuevo
            db.query(ServiceToken).filter(
                ServiceToken.usuario_id == usuario.id).delete(synchronize_session=False)
            fila, secreto = emitir_token(db, usuario, label=None)
            s.estado = "aprobada"
            s.resuelta_at = _dt.utcnow()
            s.usuario_id = usuario.id
            db.commit()
            _push_solicitud_resuelta(s, token=secreto, username=usuario.username)
            # Persistir secreto/URL del consumidor en su Application (entidad webhook)
            # para que futuras emisiones/rotaciones desde Applications auto-entreguen el token.
            try:
                from app.models import Application as _App
                _appent = db.query(_App).filter(_App.name == s.nombre,
                                                _App.deleted_at.is_(None)).first()
                if _appent is None:
                    # Crear la Application del consumidor al aprobar: queda registrada
                    # en ODM (aparece en el listado) y podrá suscribirse a recursos.
                    _appent = _App(
                        id=uuid4(),
                        name=s.nombre,
                        description=getattr(s, "descripcion", None),
                        subscribed_projects=[],
                        active=True,
                        consumption_mode=(getattr(s, "consumption_mode", None) or "webhook"),
                        webhook_url=getattr(s, "callback_url", None),
                        webhook_secret=getattr(s, "callback_secret", None),
                        persona_contacto=getattr(s, "persona_contacto", None),
                        email=getattr(s, "email", None),
                        telefono=getattr(s, "telefono", None),
                        github_url=getattr(s, "github_url", None),
                        proposito=getattr(s, "proposito", None),
                    )
                    try:
                        _appent.created_by_id = usuario.id
                    except Exception:
                        pass
                    db.add(_appent)
                else:
                    if getattr(s, "callback_url", None):
                        _appent.webhook_url = s.callback_url
                    if getattr(s, "callback_secret", None):
                        _appent.webhook_secret = s.callback_secret
                    if getattr(s, "consumption_mode", None):
                        _appent.consumption_mode = s.consumption_mode
                    for _f in ("persona_contacto", "email", "telefono", "github_url", "proposito"):
                        if getattr(_appent, _f, None) is None and getattr(s, _f, None) is not None:
                            setattr(_appent, _f, getattr(s, _f))
                    if not _appent.active:
                        _appent.active = True
                db.commit()
            except Exception:
                db.rollback()
            return AprobarSolicitudResult(
                solicitud=SolicitudIngresoType(
                    id=str(s.id), nombre=s.nombre, contacto=s.contacto, proposito=s.proposito,
                    estado=s.estado, motivo=s.motivo, created_at=getattr(s, "created_at", None),
                    resuelta_at=s.resuelta_at, usuario_id=str(usuario.id),
                ),
                usuario_id=str(usuario.id), username=usuario.username,
                token=secreto, token_prefix=fila.prefix,
            )
        except Exception:
            db.rollback(); raise
        finally:
            db.close()

    @strawberry.mutation(permission_classes=[requiere("aplicaciones.aprobar")])
    def rechazar_solicitud_ingreso(self, id: strawberry.ID, motivo: Optional[str],
                                   info: strawberry.types.Info) -> SolicitudIngresoType:
        """Rechaza una solicitud con un motivo. No crea principal ni token."""
        from app.models import SolicitudIngreso
        db = get_db()
        try:
            s = db.query(SolicitudIngreso).filter(SolicitudIngreso.id == id).first()
            if not s:
                raise ValueError("Solicitud no encontrada")
            if s.estado != "pendiente":
                raise ValueError(f"La solicitud ya está '{s.estado}'")
            s.estado = "rechazada"
            s.motivo = motivo
            s.resuelta_at = _dt.utcnow()
            db.commit()
            _push_solicitud_resuelta(s)
            return SolicitudIngresoType(
                id=str(s.id), nombre=s.nombre, contacto=s.contacto, proposito=s.proposito,
                estado=s.estado, motivo=s.motivo, created_at=getattr(s, "created_at", None),
                resuelta_at=s.resuelta_at, usuario_id=None,
            )
        except Exception:
            db.rollback(); raise
        finally:
            db.close()

    # ── §11 Gobernanza de recursos propuestos ──────────────────────────────

    @strawberry.mutation(permission_classes=[requiere("recursos.aprobar")])
    def aprobar_recurso(self, id: strawberry.ID, info: strawberry.types.Info) -> ResourceType:
        """Aprueba un recurso propuesto: pasa a 'aprobado' y queda operativo."""
        db = get_db()
        try:
            r = db.query(Resource).filter(Resource.id == id).first()
            if not r:
                raise ValueError("Recurso no encontrado")
            r.estado_aprobacion = "aprobado"
            r.motivo_rechazo = None
            db.commit()
            _push_recurso_resuelto(db, r)
            # Al quedar operativo, si tiene cadencia, se registra su job.
            if r.active and r.schedule:
                try:
                    scheduler.sync_schedule(str(r.id), r.schedule)
                except Exception:
                    pass
            return map_resource(r)
        except Exception:
            db.rollback(); raise
        finally:
            db.close()

    @strawberry.mutation(permission_classes=[requiere("recursos.aprobar")])
    def rechazar_recurso(self, id: strawberry.ID, motivo: Optional[str],
                         info: strawberry.types.Info) -> ResourceType:
        """Rechaza un recurso propuesto con un motivo; no se ejecutará."""
        db = get_db()
        try:
            r = db.query(Resource).filter(Resource.id == id).first()
            if not r:
                raise ValueError("Recurso no encontrado")
            r.estado_aprobacion = "rechazado"
            r.motivo_rechazo = motivo
            r.active = False
            db.commit()
            _push_recurso_resuelto(db, r)
            return map_resource(r)
        except Exception:
            db.rollback(); raise
        finally:
            db.close()

    # ── §12 Gestión de tokens de aplicaciones (rotar / revocar / emitir) ────

    @strawberry.mutation(permission_classes=[requiere("aplicaciones.gestionar")])
    def crear_aplicacion(self, nombre: str, contacto: Optional[str],
                         info: strawberry.types.Info) -> TokenEmitidoResult:
        """Alta manual de aplicacion M2M: materializa (idempotente) el principal
        'aplicacion' y emite su unico token Bearer. El secreto se entrega UNA vez."""
        from app.models import ServiceToken
        from app.service_auth import crear_principal_aplicacion, emitir_token
        db = get_db()
        try:
            usuario = crear_principal_aplicacion(db, nombre, contacto)
            db.query(ServiceToken).filter(
                ServiceToken.usuario_id == usuario.id).delete(synchronize_session=False)
            fila, secreto = emitir_token(db, usuario, label=None)
            db.commit()
            _push_token_a_aplicacion(db, usuario, secreto)
            return TokenEmitidoResult(token_id=str(fila.id), usuario_id=str(usuario.id),
                                      prefix=fila.prefix, token=secreto)
        except Exception:
            db.rollback(); raise
        finally:
            db.close()

    @strawberry.mutation(permission_classes=[requiere("aplicaciones.aprobar")])
    def emitir_token_aplicacion(self, usuario_id: strawberry.ID, label: Optional[str],
                                info: strawberry.types.Info) -> TokenEmitidoResult:
        """Emite un token Bearer adicional para una aplicación. El secreto en
        claro se devuelve una sola vez."""
        from app.models import Usuario
        from app.service_auth import emitir_token, PRINCIPAL_APLICACION
        db = get_db()
        try:
            u = db.query(Usuario).filter(Usuario.id == usuario_id,
                                         Usuario.tipo == PRINCIPAL_APLICACION).first()
            if not u:
                raise ValueError("Aplicación no encontrada")
            from app.models import ServiceToken
            # token único por app: borra los anteriores antes de emitir
            db.query(ServiceToken).filter(
                ServiceToken.usuario_id == u.id).delete(synchronize_session=False)
            fila, secreto = emitir_token(db, u, label=None)
            _push_token_a_aplicacion(db, u, secreto)
            return TokenEmitidoResult(token_id=str(fila.id), usuario_id=str(u.id),
                                      prefix=fila.prefix, token=secreto)
        except Exception:
            db.rollback(); raise
        finally:
            db.close()

    @strawberry.mutation(permission_classes=[requiere("aplicaciones.aprobar")])
    def rotar_token_aplicacion(self, token_id: strawberry.ID, label: Optional[str],
                               info: strawberry.types.Info) -> TokenEmitidoResult:
        """Rota un token: emite uno nuevo y revoca el anterior. Devuelve el nuevo
        secreto una sola vez."""
        from app.models import ServiceToken
        from app.service_auth import emitir_token
        db = get_db()
        try:
            tok = db.query(ServiceToken).filter(ServiceToken.id == token_id).first()
            if tok is None:
                raise ValueError("Token no encontrado")
            u = tok.usuario
            # token único: borra todos los tokens de la app y emite uno nuevo
            db.query(ServiceToken).filter(
                ServiceToken.usuario_id == tok.usuario_id).delete(synchronize_session=False)
            fila, secreto = emitir_token(db, u, label=None)
            _push_token_a_aplicacion(db, u, secreto)
            return TokenEmitidoResult(token_id=str(fila.id), usuario_id=str(fila.usuario_id),
                                      prefix=fila.prefix, token=secreto)
        except Exception:
            db.rollback(); raise
        finally:
            db.close()

    @strawberry.mutation(permission_classes=[requiere("aplicaciones.aprobar")])
    def revocar_token_aplicacion(self, token_id: strawberry.ID,
                                 info: strawberry.types.Info) -> bool:
        """Revoca un token de inmediato. Idempotente."""
        from app.service_auth import revocar_token
        db = get_db()
        try:
            ok = revocar_token(db, token_id)
            return bool(ok)
        except Exception:
            db.rollback(); raise
        finally:
            db.close()

    @strawberry.mutation(permission_classes=[requiere("aplicaciones.aprobar")])
    def eliminar_solicitud_ingreso(self, id: strawberry.ID,
                                   info: strawberry.types.Info) -> bool:
        """Elimina una solicitud de la cola (cualquier estado). Idempotente."""
        from app.models import SolicitudIngreso
        db = get_db()
        try:
            n = db.query(SolicitudIngreso).filter(
                SolicitudIngreso.id == id).delete(synchronize_session=False)
            db.commit()
            return n > 0
        except Exception:
            db.rollback(); raise
        finally:
            db.close()

