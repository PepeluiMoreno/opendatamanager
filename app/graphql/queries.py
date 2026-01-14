"""
Queries GraphQL para consultar datos.
"""
import strawberry
from typing import List, Optional
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import (
    Fetcher as FetcherModel, Resource, FetcherParams, ResourceParam, Application, FieldMetadata,
    ResourceExecution, Dataset, DatasetSubscription, ApplicationNotification
)
from app.graphql.types import (
    FetcherType,
    ResourceType,
    FetcherParamType,
    ResourceParamType,
    ApplicationType,
    FieldMetadataType,
    ResourceExecutionType,
    DatasetType,
    DatasetSubscriptionType,
    ApplicationNotificationType
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
        enum_values=getattr(p, 'enum_values', None)
    )


def map_resource_param(param: ResourceParam) -> ResourceParamType:
    """Convierte modelo ResourceParam a tipo GraphQL"""
    return ResourceParamType(
        id=str(param.id),
        key=param.key,
        value=param.value
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
        name=ft.code,  # Use code as name for display
        resources=resources if include_resources else None
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


def map_resource(resource: Resource) -> ResourceType:
    """Convierte modelo Resource a tipo GraphQL"""
    return ResourceType(
        id=str(resource.id),
        name=resource.name,
        publisher=resource.publisher,
        target_table=resource.target_table,
        active=resource.active,
        fetcher=map_fetcher(resource.fetcher) if getattr(resource, 'fetcher', None) else None,
        params=[map_resource_param(p) for p in (resource.params or [])]
    )


def map_application(app: Application) -> ApplicationType:
    """Convierte modelo Application a tipo GraphQL"""
    return ApplicationType(
        id=str(app.id),
        name=app.name,
        description=app.description,
        models_path=app.models_path,
        subscribed_projects=app.subscribed_projects or [],
        active=app.active
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
        started_at=re.started_at,
        completed_at=re.completed_at,
        status=re.status,
        total_records=re.total_records,
        records_loaded=re.records_loaded,
        staging_path=re.staging_path,
        error_message=re.error_message
    )


def map_dataset(art: Dataset) -> DatasetType:
    """Convierte modelo Dataset a tipo GraphQL"""
    return DatasetType(
        id=str(art.id),
        resource_id=str(art.resource_id),
        execution_id=str(art.execution_id) if art.execution_id else None,
        version=art.version_string,
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
            fetchers = db.query(FetcherModel).all()
            return [map_fetcher(ft, include_resources=True) for ft in fetchers]
        finally:
            db.close()

    @strawberry.field
    def fetcher(self, id: str) -> Optional[FetcherType]:
        """Obtiene un Fetcher por ID"""
        db = get_db()
        try:
            ft = db.query(FetcherModel).filter(FetcherModel.id == id).first()
            return map_fetcher(ft, include_resources=True) if ft else None
        finally:
            db.close()

    @strawberry.field
    def resources(self, active_only: bool = False) -> List[ResourceType]:
        """Lista todas las fuentes de datos"""
        db = get_db()
        try:
            query = db.query(Resource)
            if active_only:
                query = query.filter(Resource.active == True)
            resources = query.all()
            return [map_resource(r) for r in resources]
        finally:
            db.close()

    @strawberry.field
    def resource(self, id: str) -> Optional[ResourceType]:
        """Obtiene un Resource por ID"""
        db = get_db()
        try:
            resource = db.query(Resource).filter(Resource.id == id).first()
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
            apps = db.query(Application).all()
            return [map_application(app) for app in apps]
        finally:
            db.close()

    @strawberry.field
    def application(self, id: str) -> Optional[ApplicationType]:
        """Obtiene una Application por ID"""
        db = get_db()
        try:
            app = db.query(Application).filter(Application.id == id).first()
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
    def preview_resource_data(self, id: str, limit: int = 10) -> strawberry.scalars.JSON:
        """Obtiene una vista previa de los datos de un Resource sin guardarlos"""
        from app.manager.fetcher_manager import FetcherManager
        db = get_db()
        try:
            # Extraer datos solo para preview
            data = FetcherManager.fetch_only(db, id, limit)
            return data
        finally:
            db.close()

    @strawberry.field
    def resource_executions(self, resource_id: Optional[str] = None) -> List[ResourceExecutionType]:
        """Lista ejecuciones de Resources, opcionalmente filtrado por resource_id"""
        db = get_db()
        try:
            query = db.query(ResourceExecution)
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
            query = db.query(DatasetSubscription)
            if application_id:
                query = query.filter(DatasetSubscription.application_id == application_id)
            if resource_id:
                query = query.filter(DatasetSubscription.resource_id == resource_id)
            subscriptions = query.all()
            return [map_dataset_subscription(sub) for sub in subscriptions]
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
