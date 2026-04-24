"""
Queries GraphQL para consultar datos.
"""
import strawberry
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from app.database import SessionLocal
from app.models import (
    Fetcher as FetcherModel, Resource, FetcherParams, ResourceParam, Application, FieldMetadata,
    ResourceExecution, Dataset, DatasetSubscription, ApplicationNotification, AppConfig,
    DerivedDatasetConfig, DerivedDatasetEntry, Publisher
)
from app.graphql_api.types import (
    FetcherType,
    ResourceType,
    FetcherParamType,
    ResourceParamType,
    ApplicationType,
    FieldMetadataType,
    ResourceExecutionType,
    DatasetType,
    DatasetSubscriptionType,
    ApplicationNotificationType,
    AppConfigType,
    DerivedDatasetConfigType,
    PublisherType,
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
    )


def map_resource_param(param: ResourceParam) -> ResourceParamType:
    """Convierte modelo ResourceParam a tipo GraphQL"""
    return ResourceParamType(
        id=str(param.id),
        key=param.key,
        value=param.value,
        is_external=param.is_external or False
    )


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
        id=str(ft.id),
        code=ft.code,
        class_path=ft.class_path,
        description=ft.description,
        params_def=[map_type_fetcher_param(p) for p in (ft.params_def or [])],
        name=ft.code,
        resources=resources if include_resources else None,
        deleted_at=ft.deleted_at,
        created_at=ft.created_at,
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
        created_at=getattr(resource, 'created_at', None),
        deleted_at=resource.deleted_at,
        parent_resource_id=str(resource.parent_resource_id) if resource.parent_resource_id else None,
        auto_generated=getattr(resource, 'auto_generated', False) or False,
        children=children_list,
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


def map_dataset_subscription(sub: DatasetSubscription) -> DatasetSubscriptionType:
    """Convierte modelo DatasetSubscription a tipo GraphQL"""
    return DatasetSubscriptionType(
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


def map_application_notification(notif: ApplicationNotification) -> ApplicationNotificationType:
    """Convierte modelo ApplicationNotification a tipo GraphQL"""
    return ApplicationNotificationType(
        id=str(notif.id),
        application_id=str(notif.application_id),
        dataset_id=str(notif.dataset_id) if notif.dataset_id else None,
        sent_at=notif.sent_at,
        status_code=notif.status_code,
        response_body=notif.response_body,
        error_message=notif.error_message
    )




@strawberry.type
class Query:
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
    def resources(self, active_only: bool = False) -> List[ResourceType]:
        """Lista todas las fuentes de datos"""
        db = get_db()
        try:
            query = db.query(Resource).options(joinedload(Resource.publisher_obj)).filter(Resource.deleted_at == None)
            if active_only:
                query = query.filter(Resource.active == True)
            resources = query.order_by(Resource.created_at.desc()).all()
            return [map_resource(r) for r in resources]
        finally:
            db.close()

    @strawberry.field
    def resource(self, id: str) -> Optional[ResourceType]:
        """Obtiene un Resource por ID"""
        db = get_db()
        try:
            resource = db.query(Resource).filter(Resource.id == id, Resource.deleted_at == None).first()
            return map_resource(resource) if resource else None
        finally:
            db.close()

    @strawberry.field
    def resources_by_project(self, project: str) -> List[ResourceType]:
        """Lista recursos por proyecto"""
        db = get_db()
        try:
            resources = db.query(Resource).filter(Resource.project == project).all()
            return [map_resource(r) for r in resources]
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

    @strawberry.field
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
    def resource_executions(self, resource_id: Optional[str] = None) -> List[ResourceExecutionType]:
        """Lista ejecuciones de Resources, opcionalmente filtrado por resource_id"""
        db = get_db()
        try:
            query = db.query(ResourceExecution).filter(ResourceExecution.deleted_at == None)
            if resource_id:
                query = query.filter(ResourceExecution.resource_id == resource_id)
            executions = query.order_by(ResourceExecution.started_at.desc()).all()
            return [map_resource_execution(re) for re in executions]
        finally:
            db.close()

    @strawberry.field
    def resource_execution(self, id: str) -> Optional[ResourceExecutionType]:
        """Obtiene una ejecución específica por ID"""
        db = get_db()
        try:
            execution = db.query(ResourceExecution).filter(ResourceExecution.id == id).first()
            return map_resource_execution(execution) if execution else None
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
    def dataset_subscriptions(self, application_id: Optional[str] = None, resource_id: Optional[str] = None) -> List[DatasetSubscriptionType]:
        """Lista suscripciones, filtrado por application_id o resource_id"""
        db = get_db()
        try:
            query = db.query(DatasetSubscription).filter(DatasetSubscription.deleted_at == None)
            if application_id:
                query = query.filter(DatasetSubscription.application_id == application_id)
            if resource_id:
                query = query.filter(DatasetSubscription.resource_id == resource_id)
            subscriptions = query.all()
            return [map_dataset_subscription(sub) for sub in subscriptions]
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
            return [map_application_notification(notif) for notif in notifications]
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
            rows = db.query(Resource).filter(Resource.deleted_at != None).order_by(Resource.deleted_at.desc()).all()
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
    def discover_artifact(self, resource_id: strawberry.ID) -> Optional[str]:
        """Returns the latest discover artifact JSON for a resource, or null if none exists."""
        import os
        db = get_db()
        try:
            execs = (
                db.query(ResourceExecution)
                .filter(
                    ResourceExecution.resource_id == resource_id,
                    ResourceExecution.status == "completed",
                    ResourceExecution.staging_path.isnot(None),
                )
                .order_by(ResourceExecution.completed_at.desc())
                .all()
            )
            for ex in execs:
                if ex.execution_params and ex.execution_params.get("_discover_mode"):
                    if ex.staging_path and os.path.exists(ex.staging_path):
                        with open(ex.staging_path, "r", encoding="utf-8") as f:
                            return f.read()
            return None
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
