"""
Queries GraphQL para consultar datos.
"""
import strawberry
from app.rbac import requiere, puede, redactar_recurso, redactar_ejecucion
from strawberry.types import Info
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from app.database import SessionLocal
from app.models import (
    Fetcher as FetcherModel, Resource, ResourceCandidate, FetcherParams, ResourceParam, Application, FieldMetadata,
    ResourceExecution, Dataset, ResourceSubscription, ApplicationNotification, AppConfig,
    DerivedDatasetConfig, DerivedDatasetEntry, Publisher, RefrescoExtemporaneo
)
from datetime import datetime as _dt
from sqlalchemy import func as _func
from app.graphql_api.types import (
    PresetType,
    FetcherType,
    ResourceType,
    FetcherParamType,
    ResourceParamType,
    ApplicationType,
    FieldMetadataType,
    ResourceExecutionType,
    DatasetType,
    ResourceSubscriptionType,
    ApplicationNotificationType,
    AppConfigType,
    DerivedDatasetConfigType,
    PublisherType,
    ResourceCandidateType,
    SolicitudIngresoType,
    AplicacionM2MType,
    ServiceTokenType,
    TaxonomiaNodoType,
)


def get_db():
    """Helper para obtener sesión de BD"""
    db = SessionLocal()
    try:
        return db
    finally:    
        pass


def map_type_fetcher_param(p: FetcherParams) -> FetcherParamType:
    """Convierte modelo FetcherParams a tipo GraphQL"""
    return FetcherParamType(
        id=str(p.id),
        param_name=p.param_name,
        required=p.required,
        data_type=p.data_type,
        default_value=getattr(p, 'default_value', None),
        enum_values=getattr(p, 'enum_values', None),
        description=getattr(p, 'description', None),
        group=getattr(p, 'group', None),
        hint=getattr(p, 'hint', None),
        help_md=getattr(p, 'help_md', None),
        visible_when=getattr(p, 'visible_when', None),
    )


def map_resource_param(param: ResourceParam) -> ResourceParamType:
    """Convierte modelo ResourceParam a tipo GraphQL"""
    return ResourceParamType(
        id=str(param.id),
        key=param.key,
        value=param.value,
        is_external=param.is_external or False
    )


def map_preset(p) -> PresetType:
    return PresetType(id=str(p.id), code=p.code, description=p.description, params=p.params,
                      locked_params=getattr(p, "locked_params", None) or [])


def map_fetcher(ft: FetcherModel, include_resources: bool = False) -> FetcherType:
   
    if ft is None:
        return None

    # Build minimal ResourceType for fetcher list to avoid deep recursion
    resources = []
    if include_resources and ft.resources:
        for r in ft.resources:
            resources.append(ResourceType(
                id=str(r.id),
                name=r.name,
                publisher=r.publisher,
                target_table=r.target_table,
                active=r.active,
                fetcher=None,  # Don't recurse back to fetcher
                params=[]      # Don't load params for this lightweight view
            ))

    return FetcherType(
        implemented=ft.implemented,
        id=str(ft.id),
        code=ft.code,
        class_path=ft.class_path,
        description=ft.description,
        params_def=[map_type_fetcher_param(p) for p in (ft.params_def or [])],
        name=ft.code,
        resources=resources if include_resources else None,
        deleted_at=ft.deleted_at,
        created_at=ft.created_at,
        preset_params=getattr(ft, 'preset_params', None),
        modos=getattr(ft, 'modos', None) or ["extraer"],
        presets=[map_preset(pr) for pr in (getattr(ft, 'presets', None) or []) if pr.deleted_at is None] or None,
    )


""" def map_fetcher(ft: FetcherModel) -> Optional[Fetcher]:
      
    if ft is None:
        return None

    return Fetcher(
        id=str(ft.id),
        code=ft.code,
        name=ft.code,
        class_path=ft.class_path,
        description=ft.description,
        params_def=[map_type_fetcher_param(p) for p in (ft.params_def or [])],
        resources=None,
    ) """


def map_publisher(p: Publisher) -> PublisherType:
    return PublisherType(
        id=str(p.id),
        nombre=p.nombre,
        acronimo=p.acronimo,
        nivel=p.nivel,
        pais=p.pais,
        comunidad_autonoma=p.comunidad_autonoma,
        provincia=p.provincia,
        municipio=p.municipio,
        portal_url=p.portal_url,
        email=p.email,
        telefono=p.telefono,
        created_at=p.created_at,
        deleted_at=p.deleted_at,
    )


def _created_by_kind(resource: Resource) -> str:
    """Eje humano de procedencia: quién generó el recurso.
    - 'sistema'    : derivado automáticamente (crawler/discover).
    - 'aplicacion' : creado programáticamente (importManifest / seed).
    - 'usuario'    : creado a mano en la UI.
    El antiguo 'origin' (ui|manifest|seed) queda como detalle interno del cómo."""
    if getattr(resource, "auto_generated", False):
        return "sistema"
    if getattr(resource, "origin", None) in ("manifest", "seed"):
        return "aplicacion"
    return "usuario"


def map_resource(resource: Resource) -> ResourceType:
    """Convierte modelo Resource a tipo GraphQL"""
    pub_obj = getattr(resource, 'publisher_obj', None)
    children_list = None
    if getattr(resource, '_include_children', False):
        try:
            children_list = [map_resource(c) for c in resource.children.filter_by(deleted_at=None).all()]
        except Exception:
            children_list = []
    return ResourceType(
        last_tested_at=getattr(resource, 'last_tested_at', None),
        origin=getattr(resource, 'origin', None),
        id=str(resource.id),
        name=resource.name,
        description=resource.description,
        publisher=resource.publisher,
        publisher_id=str(resource.publisher_id) if resource.publisher_id else None,
        publisher_obj=map_publisher(pub_obj) if pub_obj else None,
        target_table=resource.target_table,
        active=resource.active,
        schedule=resource.schedule,
        fetcher=map_fetcher(resource.fetcher) if getattr(resource, 'fetcher', None) else None,
        params=[map_resource_param(p) for p in (resource.params or [])],
        preset=(map_preset(resource.preset)
                if getattr(resource, 'preset', None) and resource.preset.deleted_at is None else None),
        created_at=getattr(resource, 'created_at', None),
        deleted_at=resource.deleted_at,
        parent_resource_id=str(resource.parent_resource_id) if resource.parent_resource_id else None,
        auto_generated=getattr(resource, 'auto_generated', False) or False,
        genera_colecciones=bool(getattr(resource, 'genera_colecciones', False)),
        created_by_kind=_created_by_kind(resource),
        subscriber_count=getattr(resource, '_subscriber_count', 0),
        subscriber_apps=getattr(resource, '_subscriber_apps', None),
        children=children_list,
        es_coleccion=bool(getattr(resource, 'es_coleccion', False)),
        estado_aprobacion=getattr(resource, 'estado_aprobacion', 'aprobado') or 'aprobado',
        motivo_rechazo=getattr(resource, 'motivo_rechazo', None),
        candidatos_pendientes=getattr(resource, '_candidatos_pendientes', 0),
        miembros=getattr(resource, '_miembros', 0),
        ultimo_descubrimiento=getattr(resource, '_ultimo_descubrimiento', None),
    )


def map_application(app: Application) -> ApplicationType:
    """Convierte modelo Application a tipo GraphQL"""
    return ApplicationType(
        id=str(app.id),
        name=app.name,
        description=app.description,
        models_path=app.models_path,
        subscribed_projects=app.subscribed_projects or [],
        active=app.active,
        webhook_url=app.webhook_url,
        consumption_mode=app.consumption_mode or "webhook",
        persona_contacto=getattr(app, "persona_contacto", None),
        email=getattr(app, "email", None),
        telefono=getattr(app, "telefono", None),
        github_url=getattr(app, "github_url", None),
        proposito=getattr(app, "proposito", None),
        deleted_at=app.deleted_at,
    )


def map_field_metadata(fm: FieldMetadata) -> FieldMetadataType:
    """Convierte modelo FieldMetadata a tipo GraphQL"""
    return FieldMetadataType(
        id=str(fm.id),
        table_name=fm.table_name,
        field_name=fm.field_name,
        label=fm.label,
        help_text=fm.help_text,
        placeholder=fm.placeholder
    )


def map_resource_execution(re: ResourceExecution) -> ResourceExecutionType:
    """Convierte modelo ResourceExecution a tipo GraphQL"""
    return ResourceExecutionType(
        id=str(re.id),
        resource_id=str(re.resource_id),
        resource_name=re.resource_name,
        started_at=re.started_at,
        completed_at=re.completed_at,
        status=re.status,
        total_records=re.total_records,
        records_loaded=re.records_loaded,
        staging_path=re.staging_path,
        error_message=re.error_message,
        execution_params=re.execution_params,
        pause_requested=bool(re.pause_requested),
        active_seconds=re.active_seconds,
        deleted_at=re.deleted_at,
    )


def map_resource_candidate(c: ResourceCandidate) -> ResourceCandidateType:
    """Convierte modelo ResourceCandidate a tipo GraphQL"""
    return ResourceCandidateType(
        id=str(c.id),
        execution_id=str(c.execution_id) if c.execution_id else None,
        crawler_resource_id=str(c.crawler_resource_id),
        path_template=c.path_template,
        dimensions=c.dimensions or [],
        matched_urls=c.matched_urls or [],
        file_types=c.file_types or {},
        suggested_name=c.suggested_name,
        confidence=c.confidence,
        status=c.status,
        promoted_resource_id=str(c.promoted_resource_id) if c.promoted_resource_id else None,
        merged_into_id=str(c.merged_into_id) if c.merged_into_id else None,
        split_from_id=str(c.split_from_id) if c.split_from_id else None,
        detected_at=c.detected_at,
        reviewed_at=c.reviewed_at,
        reviewed_by=c.reviewed_by,
        deleted_at=c.deleted_at,
    )


def map_dataset(art: Dataset) -> DatasetType:
    """Convierte modelo Dataset a tipo GraphQL"""
    return DatasetType(
        id=str(art.id),
        resource_id=str(art.resource_id),
        execution_id=str(art.execution_id) if art.execution_id else None,
        version=art.version_string,
        label=art.label,
        major_version=art.major_version,
        minor_version=art.minor_version,
        patch_version=art.patch_version,
        schema_json=art.schema_json,
        data_path=art.data_path,
        record_count=art.record_count,
        checksum=art.checksum,
        created_at=art.created_at,
        download_urls={
            "data": f"/api/datasets/{art.id}/data.jsonl",
            "schema": f"/api/datasets/{art.id}/schema.json",
            "models": f"/api/datasets/{art.id}/models.py",
            "metadata": f"/api/datasets/{art.id}/metadata.json"
        }
    )


def map_resource_subscription(sub: ResourceSubscription) -> ResourceSubscriptionType:
    """Convierte modelo ResourceSubscription a tipo GraphQL"""
    return ResourceSubscriptionType(
        id=str(sub.id),
        application_id=str(sub.application_id),
        resource_id=str(sub.resource_id),
        pinned_version=sub.pinned_version,
        auto_upgrade=sub.auto_upgrade,
        current_version=sub.current_version,
        notified_at=sub.notified_at
    )


def map_derived_dataset_config(cfg: DerivedDatasetConfig, entry_count: int = None) -> DerivedDatasetConfigType:
    """Convierte modelo DerivedDatasetConfig a tipo GraphQL"""
    return DerivedDatasetConfigType(
        id=str(cfg.id),
        source_resource_id=str(cfg.source_resource_id),
        target_name=cfg.target_name,
        key_field=cfg.key_field,
        extract_fields=cfg.extract_fields or [],
        merge_strategy=cfg.merge_strategy or "upsert",
        enabled=cfg.enabled,
        description=cfg.description,
        created_at=cfg.created_at,
        entry_count=entry_count,
    )


def map_application_notification(notif: ApplicationNotification, publisher=None, dataset_name=None) -> ApplicationNotificationType:
    """Convierte modelo ApplicationNotification a tipo GraphQL"""
    return ApplicationNotificationType(
        id=str(notif.id),
        application_id=str(notif.application_id),
        dataset_id=str(notif.dataset_id) if notif.dataset_id else None,
        sent_at=notif.sent_at,
        status_code=notif.status_code,
        response_body=notif.response_body,
        error_message=notif.error_message,
        publisher=publisher,
        dataset_name=dataset_name,
    )




@strawberry.type
class CuotaRefrescos:
    """Cuota diaria de refrescos a demanda del principal (hoy)."""
    limite: int
    usados_hoy: int
    restantes: int


@strawberry.type
class UsoMensualAplicacion:
    """Uso de refrescos a demanda de una aplicación en el mes en curso."""
    usados: int
    periodo: str
    cuota_diaria: int = strawberry.field(name="cuotaDiaria")


@strawberry.type
class Query:
    @strawberry.field
    def whoami_aplicacion(self, info: Info) -> Optional[str]:
        """Username del principal 'aplicacion' autenticado por Bearer, o null si
        el token no es válido / no es una aplicación. El consumidor lo usa para
        validar al arrancar si sigue dado de alta (token vivo)."""
        from app.service_auth import PRINCIPAL_APLICACION
        usuario = info.context.get("usuario") if (info and info.context) else None
        if usuario is not None and getattr(usuario, "tipo", None) == PRINCIPAL_APLICACION:
            return usuario.username
        return None

    @strawberry.field
    def cuota_refrescos(self, info: Info) -> CuotaRefrescos:
        """Cuota de refrescos a demanda del principal actual, recalculada hoy."""
        usuario = info.context.get("usuario") if (info and info.context) else None
        if usuario is None:
            return CuotaRefrescos(limite=0, usados_hoy=0, restantes=0)
        db = get_db()
        try:
            limite = getattr(usuario, "cuota_refrescos_diaria", 0) or 0
            inicio = _dt.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            usados = db.query(_func.count(RefrescoExtemporaneo.id)).filter(
                RefrescoExtemporaneo.created_by_id == usuario.id,
                RefrescoExtemporaneo.created_at >= inicio,
            ).scalar() or 0
            return CuotaRefrescos(limite=limite, usados_hoy=usados, restantes=max(0, limite - usados))
        finally:
            db.close()

    @strawberry.field
    def uso_mensual_aplicacion(self, application_id: str) -> UsoMensualAplicacion:
        """Refrescos a demanda consumidos por la aplicación en el mes en curso.
        Resuelve el principal por nombre (Application.name == Usuario.username)."""
        from app.models import Application, Usuario, RefrescoExtemporaneo
        db = get_db()
        now = _dt.utcnow()
        periodo = now.strftime("%Y-%m")
        try:
            inicio = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            app_row = db.query(Application).filter(Application.id == application_id).first()
            u = db.query(Usuario).filter(Usuario.username == app_row.name).first() if app_row else None
            if u is None:
                return UsoMensualAplicacion(usados=0, periodo=periodo, cuota_diaria=0)
            usados = db.query(_func.count(RefrescoExtemporaneo.id)).filter(
                RefrescoExtemporaneo.created_by_id == u.id,
                RefrescoExtemporaneo.created_at >= inicio,
            ).scalar() or 0
            cuota = getattr(u, "cuota_refrescos_diaria", 0) or 0
            return UsoMensualAplicacion(usados=usados, periodo=periodo, cuota_diaria=cuota)
        finally:
            db.close()

    @strawberry.field
    def resource_manifest(self, id: str) -> strawberry.scalars.JSON:
        """Exporta un recurso como manifiesto JSON importable.

        Queda protegida por la autenticación de /graphql.
        """
        from app.services.manifests import build_manifest
        from app.models import Resource as ResourceM, ResourceParam as ResourceParamM, Fetcher as FetcherM, Publisher as PublisherM
        db = get_db()
        try:
            resource = db.query(ResourceM).filter(ResourceM.id == id, ResourceM.deleted_at == None).first()
            if not resource:
                return {"error": f"Resource '{id}' no encontrado"}
            fetcher = db.query(FetcherM).filter(FetcherM.id == resource.fetcher_id).first()
            publisher = (
                db.query(PublisherM).filter(PublisherM.id == resource.publisher_id).first()
                if resource.publisher_id else None
            )
            params = db.query(ResourceParamM).filter(ResourceParamM.resource_id == resource.id).all()
            return build_manifest(publisher, [(resource, fetcher, params)])
        finally:
            db.close()

    @strawberry.field
    def manifest_template(self, fetcher_code: str, preset_code: Optional[str] = None) -> strawberry.scalars.JSON:
        """Devuelve un manifiesto-plantilla para un fetcher (y, opcionalmente, una
        variante/preset), listo para descargar, rellenar e importar.

        Los params del preset se incluyen como punto de partida; el bloque
        `_plantilla` lleva las instrucciones. Protegida por la auth de /graphql.
        """
        from app.services.manifests import template_manifest
        from app.models import Fetcher as FetcherM, FetcherPreset as FetcherPresetM
        db = get_db()
        try:
            fetcher = db.query(FetcherM).filter(FetcherM.code == fetcher_code).first()
            if not fetcher:
                return {"error": f"Fetcher con code '{fetcher_code}' no encontrado"}
            presets = (db.query(FetcherPresetM)
                       .filter(FetcherPresetM.fetcher_id == fetcher.id,
                               FetcherPresetM.deleted_at.is_(None)).all())
            preset = None
            if preset_code:
                preset = next((p for p in presets if p.code == preset_code), None)
                if preset is None:
                    return {"error": f"Preset '{preset_code}' no existe bajo el fetcher '{fetcher_code}'"}
            return template_manifest(
                fetcher.code,
                preset_code=preset.code if preset else None,
                preset_params=(preset.params if preset else None),
                locked_params=(preset.locked_params if preset else None),
                available_presets=([p.code for p in presets] if not preset else None),
            )
        finally:
            db.close()

    @strawberry.field
    def fetchers(self) -> List[FetcherType]:
        """Lista todos los fetchers disponibles"""
        db = get_db()
        try:
            fetchers = db.query(FetcherModel).filter(FetcherModel.deleted_at == None).all()
            return [map_fetcher(ft, include_resources=True) for ft in fetchers]
        finally:
            db.close()

    @strawberry.field
    def fetcher(self, id: str) -> Optional[FetcherType]:
        """Obtiene un Fetcher por ID"""
        db = get_db()
        try:
            ft = db.query(FetcherModel).filter(FetcherModel.id == id, FetcherModel.deleted_at == None).first()
            return map_fetcher(ft, include_resources=True) if ft else None
        finally:
            db.close()

    @strawberry.field
    def resources(self, info: Info, active_only: bool = False,
                  used_by: Optional[str] = None,
                  created_by: Optional[str] = None) -> List[ResourceType]:
        """Lista todas las fuentes de datos.

        `used_by`: id de una aplicación → solo los recursos a los que está suscrita
        (ver las aplicaciones desde los recursos, como los recursos desde las apps).
        """
        db = get_db()
        try:
            query = db.query(Resource).options(joinedload(Resource.publisher_obj)).filter(Resource.deleted_at == None)
            if active_only:
                query = query.filter(Resource.active == True)
            resources = query.order_by(Resource.created_at.desc()).all()

            # Aplicaciones suscritas por recurso, en bloque (sin N+1): nombres
            # para mostrar e ids para filtrar.
            nombres_por_recurso: dict = {}
            ids_por_recurso: dict = {}
            subs = (
                db.query(ResourceSubscription.resource_id, Application.id, Application.name)
                .join(Application, Application.id == ResourceSubscription.application_id)
                .filter(ResourceSubscription.deleted_at == None,
                        Application.deleted_at == None)
                .all()
            )
            for rid, app_id, app_name in subs:
                nombres_por_recurso.setdefault(rid, []).append(app_name)
                ids_por_recurso.setdefault(rid, set()).add(str(app_id))

            if used_by:
                resources = [r for r in resources if used_by in ids_por_recurso.get(r.id, set())]
            if created_by:
                resources = [r for r in resources if _created_by_kind(r) == created_by]

            for r in resources:
                nombres = nombres_por_recurso.get(r.id, [])
                r._subscriber_apps = nombres or None
                r._subscriber_count = len(nombres)

            out = [map_resource(r) for r in resources]
            if not puede(info, "recursos.ver_sensible"):
                for rt in out:
                    redactar_recurso(rt)
            return out
        finally:
            db.close()

    @strawberry.field
    def collections(self, info: Info) -> List[ResourceType]:
        """Las naves nodriza: recursos cuya especie declara el modo 'descubrir'
        (es_coleccion). Para cada una, candidatos pendientes, miembros
        promovidos y fecha del último rastreo."""
        db = get_db()
        try:
            base = (db.query(Resource)
                    .options(joinedload(Resource.publisher_obj))
                    .filter(Resource.deleted_at == None,
                            Resource.parent_resource_id == None,
                            Resource.genera_colecciones == True)
                    .order_by(Resource.created_at.desc()).all())
            cols = [r for r in base if r.es_coleccion]
            for r in cols:
                r._candidatos_pendientes = (db.query(ResourceCandidate)
                    .filter(ResourceCandidate.crawler_resource_id == r.id,
                            ResourceCandidate.status == "discovered").count())
                r._miembros = (db.query(Resource)
                    .filter(Resource.parent_resource_id == r.id,
                            Resource.deleted_at == None).count())
                ult = (db.query(ResourceExecution)
                    .filter(ResourceExecution.resource_id == r.id,
                            ResourceExecution.kind == "discovering")
                    .order_by(ResourceExecution.started_at.desc()).first())
                r._ultimo_descubrimiento = ult.started_at if ult else None
            out = [map_resource(r) for r in cols]
            if not puede(info, "recursos.ver_sensible"):
                for rt in out:
                    redactar_recurso(rt)
            return out
        finally:
            db.close()

    @strawberry.field
    def resource(self, info: Info, id: str) -> Optional[ResourceType]:
        """Obtiene un Resource por ID"""
        db = get_db()
        try:
            resource = db.query(Resource).filter(Resource.id == id, Resource.deleted_at == None).first()
            rt = map_resource(resource) if resource else None
            if rt is not None and not puede(info, "recursos.ver_sensible"):
                redactar_recurso(rt)
            return rt
        finally:
            db.close()

    @strawberry.field
    def resources_by_project(self, info: Info, project: str) -> List[ResourceType]:
        """Lista recursos por proyecto"""
        db = get_db()
        try:
            resources = db.query(Resource).filter(Resource.project == project).all()
            out = [map_resource(r) for r in resources]
            if not puede(info, "recursos.ver_sensible"):
                for rt in out:
                    redactar_recurso(rt)
            return out
        finally:
            db.close()

    @strawberry.field
    def applications(self) -> List[ApplicationType]:
        """Lista todas las aplicaciones suscritas"""
        db = get_db()
        try:
            apps = db.query(Application).filter(Application.deleted_at == None).all()
            return [map_application(app) for app in apps]
        finally:
            db.close()

    @strawberry.field
    def application(self, id: str) -> Optional[ApplicationType]:
        """Obtiene una Application por ID"""
        db = get_db()
        try:
            app = db.query(Application).filter(Application.id == id, Application.deleted_at == None).first()
            return map_application(app) if app else None
        finally:
            db.close()

    @strawberry.field
    def field_metadata(self, table_name: str) -> List[FieldMetadataType]:
        """Obtiene metadata de campos para una tabla"""
        db = get_db()
        try:
            metadata = db.query(FieldMetadata).filter(
                FieldMetadata.table_name == table_name
            ).all()
            return [map_field_metadata(fm) for fm in metadata]
        finally:
            db.close()

    @strawberry.field(permission_classes=[requiere("recursos.testar")])
    async def preview_resource_data(self, id: str, limit: int = 10, params: Optional[strawberry.scalars.JSON] = None) -> strawberry.scalars.JSON:
        """Obtiene una vista previa de los datos de un Resource sin guardarlos"""
        import asyncio
        from app.manager.fetcher_manager import FetcherManager

        def _fetch():
            db = get_db()
            try:
                return {"records": FetcherManager.fetch_only(db, id, limit, runtime_params=params or {}), "error": None}
            except Exception as e:
                return {"records": [], "error": str(e)}
            finally:
                db.close()

        return await asyncio.to_thread(_fetch)

    @strawberry.field
    def resource_executions(self, info: Info, resource_id: Optional[str] = None) -> List[ResourceExecutionType]:
        """Lista ejecuciones de Resources, opcionalmente filtrado por resource_id"""
        db = get_db()
        try:
            query = db.query(ResourceExecution).filter(ResourceExecution.deleted_at == None)
            if resource_id:
                query = query.filter(ResourceExecution.resource_id == resource_id)
            executions = query.order_by(ResourceExecution.started_at.desc()).all()
            out = [map_resource_execution(re) for re in executions]
            if not puede(info, "recursos.ver_sensible"):
                for et in out:
                    redactar_ejecucion(et)
            return out
        finally:
            db.close()

    @strawberry.field
    def resource_execution(self, info: Info, id: str) -> Optional[ResourceExecutionType]:
        """Obtiene una ejecución específica por ID"""
        db = get_db()
        try:
            execution = db.query(ResourceExecution).filter(ResourceExecution.id == id).first()
            et = map_resource_execution(execution) if execution else None
            if et is not None and not puede(info, "recursos.ver_sensible"):
                redactar_ejecucion(et)
            return et
        finally:
            db.close()

    @strawberry.field
    def app_config(self) -> List[AppConfigType]:
        """Returns all application settings."""
        db = get_db()
        try:
            rows = db.query(AppConfig).order_by(AppConfig.key).all()
            return [
                AppConfigType(key=r.key, value=r.value, description=r.description, updated_at=r.updated_at)
                for r in rows
            ]
        finally:
            db.close()

    @strawberry.field
    def datasets(self, resource_id: Optional[str] = None) -> List[DatasetType]:
        """Lista datasets, opcionalmente filtrado por resource_id"""
        db = get_db()
        try:
            query = db.query(Dataset)
            if resource_id:
                query = query.filter(Dataset.resource_id == resource_id)
            datasets = query.order_by(
                Dataset.major_version.desc(),
                Dataset.minor_version.desc(),
                Dataset.patch_version.desc()
            ).all()
            return [map_dataset(art) for art in datasets]
        finally:
            db.close()

    @strawberry.field
    def dataset(self, id: str) -> Optional[DatasetType]:
        """Obtiene un dataset específico por ID"""
        db = get_db()
        try:
            dataset = db.query(Dataset).filter(Dataset.id == id).first()
            return map_dataset(dataset) if dataset else None
        finally:
            db.close()

    @strawberry.field
    def dataset_by_version(self, resource_id: str, version: str) -> Optional[DatasetType]:
        """Obtiene un dataset por resource_id y version (ej: '1.2.3')"""
        db = get_db()
        try:
            parts = version.split('.')
            if len(parts) != 3:
                return None
            major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

            dataset = db.query(Dataset).filter(
                Dataset.resource_id == resource_id,
                Dataset.major_version == major,
                Dataset.minor_version == minor,
                Dataset.patch_version == patch
            ).first()
            return map_dataset(dataset) if dataset else None
        finally:
            db.close()

    @strawberry.field
    def resource_subscriptions(self, application_id: Optional[str] = None, resource_id: Optional[str] = None) -> List[ResourceSubscriptionType]:
        """Lista suscripciones, filtrado por application_id o resource_id"""
        db = get_db()
        try:
            query = db.query(ResourceSubscription).filter(ResourceSubscription.deleted_at == None)
            if application_id:
                query = query.filter(ResourceSubscription.application_id == application_id)
            if resource_id:
                query = query.filter(ResourceSubscription.resource_id == resource_id)
            subscriptions = query.all()
            return [map_resource_subscription(sub) for sub in subscriptions]
        finally:
            db.close()

    @strawberry.field
    def derived_dataset_configs(self, source_resource_id: Optional[str] = None) -> List[DerivedDatasetConfigType]:
        """Lista configuraciones de datasets derivados, opcionalmente filtrado por source_resource_id"""
        db = get_db()
        try:
            query = db.query(DerivedDatasetConfig).filter(DerivedDatasetConfig.deleted_at == None)
            if source_resource_id:
                query = query.filter(DerivedDatasetConfig.source_resource_id == source_resource_id)
            configs = query.order_by(DerivedDatasetConfig.created_at).all()
            result = []
            for cfg in configs:
                count = db.query(DerivedDatasetEntry).filter(
                    DerivedDatasetEntry.config_id == cfg.id
                ).count()
                result.append(map_derived_dataset_config(cfg, entry_count=count))
            return result
        finally:
            db.close()

    @strawberry.field
    def application_notifications(self, application_id: Optional[str] = None, dataset_id: Optional[str] = None) -> List[ApplicationNotificationType]:
        """Lista notificaciones enviadas, filtrado por application_id o dataset_id"""
        db = get_db()
        try:
            query = db.query(ApplicationNotification)
            if application_id:
                query = query.filter(ApplicationNotification.application_id == application_id)
            if dataset_id:
                query = query.filter(ApplicationNotification.dataset_id == dataset_id)
            notifications = query.order_by(ApplicationNotification.sent_at.desc()).all()
            # Enriquecer con publisher/nombre del dataset (para filtrar en el consumidor)
            ds_ids = {n.dataset_id for n in notifications if n.dataset_id}
            info = {}
            if ds_ids:
                from app.models import Dataset, Resource
                for did, pub, rname in (db.query(Dataset.id, Resource.publisher, Resource.name)
                                          .join(Resource, Dataset.resource_id == Resource.id)
                                          .filter(Dataset.id.in_(ds_ids)).all()):
                    info[str(did)] = (pub, rname)
            return [map_application_notification(n, *info.get(str(n.dataset_id), (None, None))) for n in notifications]
        finally:
            db.close()

    @strawberry.field
    def publishers(self) -> List[PublisherType]:
        """Lista todos los publishers ordenados por nombre"""
        db = get_db()
        try:
            return [map_publisher(p) for p in db.query(Publisher).filter(Publisher.deleted_at == None).order_by(Publisher.nombre).all()]
        finally:
            db.close()

    @strawberry.field
    def publisher(self, id: str) -> Optional[PublisherType]:
        """Obtiene un Publisher por ID"""
        db = get_db()
        try:
            p = db.query(Publisher).filter(Publisher.id == id, Publisher.deleted_at == None).first()
            return map_publisher(p) if p else None
        finally:
            db.close()

    # ── Trash queries ──────────────────────────────────────────────────────────

    @strawberry.field
    def deleted_resources(self) -> List[ResourceType]:
        db = get_db()
        try:
            rows = db.query(Resource).filter(
                Resource.deleted_at != None,
                Resource.auto_generated.isnot(True),
            ).order_by(Resource.deleted_at.desc()).all()
            return [map_resource(r) for r in rows]
        finally:
            db.close()

    @strawberry.field
    def deleted_applications(self) -> List[ApplicationType]:
        db = get_db()
        try:
            rows = db.query(Application).filter(Application.deleted_at != None).order_by(Application.deleted_at.desc()).all()
            return [map_application(a) for a in rows]
        finally:
            db.close()

    @strawberry.field
    def deleted_publishers(self) -> List[PublisherType]:
        db = get_db()
        try:
            rows = db.query(Publisher).filter(Publisher.deleted_at != None).order_by(Publisher.deleted_at.desc()).all()
            return [map_publisher(p) for p in rows]
        finally:
            db.close()

    @strawberry.field
    def deleted_fetchers(self) -> List[FetcherType]:
        db = get_db()
        try:
            rows = db.query(FetcherModel).filter(FetcherModel.deleted_at != None).order_by(FetcherModel.deleted_at.desc()).all()
            return [map_fetcher(ft) for ft in rows]
        finally:
            db.close()

    @strawberry.field
    def deleted_executions(self) -> List[ResourceExecutionType]:
        db = get_db()
        try:
            rows = db.query(ResourceExecution).filter(ResourceExecution.deleted_at != None).order_by(ResourceExecution.deleted_at.desc()).all()
            return [map_resource_execution(e) for e in rows]
        finally:
            db.close()

    @strawberry.field
    def taxonomia_crawler(self, crawler_resource_id: strawberry.ID) -> List[TaxonomiaNodoType]:
        """Árbol de ramas (taxonomía) derivado al vuelo de los candidatos
        `discovered` del crawler: segmentos de ruta constantes con agregados por
        nodo. Vista para navegar el portal y promover ramas enteras de una vez,
        en lugar de candidato a candidato. Soft-deleted excluidos."""
        from app.services.taxonomia import construir_taxonomia
        db = get_db()
        try:
            rows = (
                db.query(ResourceCandidate)
                .filter(
                    ResourceCandidate.deleted_at.is_(None),
                    ResourceCandidate.crawler_resource_id == crawler_resource_id,
                    ResourceCandidate.status == "discovered",
                )
                .all()
            )
            items = [{
                "id": str(r.id),
                "path_template": r.path_template,
                "matched_urls": r.matched_urls,
                "file_types": r.file_types,
                "dimensions": r.dimensions,
                "suggested_name": r.suggested_name,
            } for r in rows]
            return [
                TaxonomiaNodoType(
                    path=n["path"], label=n["label"], parent=n["parent"], depth=n["depth"],
                    num_candidatos=n["num_candidatos"], num_directos=n["num_directos"],
                    num_urls=n["num_urls"], formatos=n["formatos"], dimensiones=n["dimensiones"],
                    candidato_ids=[str(x) for x in n["candidato_ids"]],
                )
                for n in construir_taxonomia(items)
            ]
        finally:
            db.close()

    @strawberry.field
    def resource_candidates(
        self,
        crawler_resource_id: Optional[strawberry.ID] = None,
        execution_id: Optional[strawberry.ID] = None,
        status: Optional[str] = None,
    ) -> List[ResourceCandidateType]:
        """Lista candidatos generados por el GroupingInferer tras un discover.
        Filtros opcionales: crawler, ejecución, estado. Soft-deleted excluidos."""
        db = get_db()
        try:
            q = db.query(ResourceCandidate).filter(ResourceCandidate.deleted_at.is_(None))
            if crawler_resource_id:
                q = q.filter(ResourceCandidate.crawler_resource_id == crawler_resource_id)
            if execution_id:
                q = q.filter(ResourceCandidate.execution_id == execution_id)
            if status:
                q = q.filter(ResourceCandidate.status == status)
            rows = q.order_by(
                ResourceCandidate.confidence.desc().nullslast(),
                ResourceCandidate.detected_at.desc(),
            ).all()
            return [map_resource_candidate(c) for c in rows]
        finally:
            db.close()

    @strawberry.field
    def resource_candidate(self, id: strawberry.ID) -> Optional[ResourceCandidateType]:
        db = get_db()
        try:
            c = db.query(ResourceCandidate).filter(ResourceCandidate.id == id).first()
            return map_resource_candidate(c) if c else None
        finally:
            db.close()

    @strawberry.field
    def resource_children(self, parent_resource_id: strawberry.ID) -> List[ResourceType]:
        """Returns all child resources created from a discover run."""
        db = get_db()
        try:
            rows = (
                db.query(Resource)
                .filter(
                    Resource.parent_resource_id == parent_resource_id,
                    Resource.deleted_at == None,
                )
                .order_by(Resource.name)
                .all()
            )
            return [map_resource(r) for r in rows]
        finally:
            db.close()

    @strawberry.field(permission_classes=[requiere("aplicaciones.aprobar")])
    def solicitudes_ingreso(self, info: Info, solo_pendientes: bool = True) -> List[SolicitudIngresoType]:
        """Cola de solicitudes de alta de aplicaciones (§12). Requiere
        'aplicaciones.aprobar'."""
        from app.models import SolicitudIngreso
        db = SessionLocal()
        try:
            q = db.query(SolicitudIngreso)
            if solo_pendientes:
                q = q.filter(SolicitudIngreso.estado == "pendiente")
            rows = q.order_by(SolicitudIngreso.created_at.desc()).all()
            from app.models import Application as _App
            _names = {r[0] for r in db.query(_App.name).filter(_App.deleted_at == None).all()}
            return [SolicitudIngresoType(
                id=str(s.id), nombre=s.nombre, contacto=s.contacto, proposito=s.proposito,
                descripcion=getattr(s, "descripcion", None), persona_contacto=getattr(s, "persona_contacto", None),
                email=getattr(s, "email", None), telefono=getattr(s, "telefono", None),
                github_url=getattr(s, "github_url", None),
                consumption_mode=getattr(s, "consumption_mode", None),
                webhook_url=getattr(s, "callback_url", None),
                ya_registrada=(s.nombre in _names),
                estado=s.estado, motivo=s.motivo, created_at=getattr(s, "created_at", None),
                resuelta_at=s.resuelta_at,
                usuario_id=str(s.usuario_id) if s.usuario_id else None,
            ) for s in rows]
        finally:
            db.close()

    @strawberry.field(permission_classes=[requiere("recursos.aprobar")])
    def recursos_propuestos(self, info: Info) -> List[ResourceType]:
        """Cola de recursos propuestos por aplicaciones, pendientes de
        aprobación (§11). Requiere 'recursos.aprobar'."""
        db = SessionLocal()
        try:
            rows = (db.query(Resource)
                    .options(joinedload(Resource.publisher_obj))
                    .filter(Resource.deleted_at == None,
                            Resource.estado_aprobacion == "pendiente")
                    .order_by(Resource.created_at.desc()).all())
            return [map_resource(r) for r in rows]
        finally:
            db.close()

    @strawberry.field(permission_classes=[requiere("aplicaciones.aprobar")])
    def aplicaciones_m2m(self, info: Info) -> List[AplicacionM2MType]:
        """Aplicaciones aprobadas (principales tipo='aplicacion') y sus tokens
        Bearer, sin el secreto (solo metadatos). Requiere 'aplicaciones.aprobar'."""
        from app.models import Usuario, ServiceToken
        from app.service_auth import PRINCIPAL_APLICACION
        db = SessionLocal()
        try:
            ahora = _dt.utcnow()
            apps = (db.query(Usuario)
                    .filter(Usuario.tipo == PRINCIPAL_APLICACION)
                    .order_by(Usuario.username).all())
            out = []
            for u in apps:
                toks = (db.query(ServiceToken)
                        .filter(ServiceToken.usuario_id == u.id)
                        .order_by(ServiceToken.created_at.desc()).all())
                out.append(AplicacionM2MType(
                    usuario_id=str(u.id), username=u.username, email=u.email, is_active=u.is_active,
                    tokens=[ServiceTokenType(
                        id=str(t.id), label=t.label, prefix=t.prefix,
                        last_used_at=t.last_used_at, expires_at=t.expires_at, revoked_at=t.revoked_at,
                        activo=(t.revoked_at is None and (t.expires_at is None or t.expires_at > ahora)),
                    ) for t in toks],
                ))
            return out
        finally:
            db.close()
