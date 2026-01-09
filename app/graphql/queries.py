"""
Queries GraphQL para consultar datos.
"""
import strawberry
from typing import List, Optional
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import FetcherType, Resource, TypeFetcherParams, ResourceParam, Application, FieldMetadata
from app.graphql.types import (
    FetcherTypeType,
    ResourceType,
    TypeFetcherParamType,
    ResourceParamType,
    ApplicationType,
    FieldMetadataType
)


def get_db():
    """Helper para obtener sesión de BD"""
    db = SessionLocal()
    try:
        return db
    finally:
        pass


def map_fetcher_type(ft: FetcherType) -> FetcherTypeType:
    """Convierte modelo FetcherType a tipo GraphQL"""
    return FetcherTypeType(
        id=str(ft.id),
        code=ft.code,
        class_path=ft.class_path,
        description=ft.description,
        params_def=ft.params_def
    )


def map_resource_param(param: ResourceParam) -> ResourceParamType:
    """Convierte modelo ResourceParam a tipo GraphQL"""
    return ResourceParamType(
        id=str(param.id),
        key=param.key,
        value=param.value
    )


def map_resource(resource: Resource) -> ResourceType:
    """Convierte modelo Resource a tipo GraphQL"""
    return ResourceType(
        id=str(resource.id),
        name=resource.name,
        publisher=resource.publisher,
        target_table=resource.target_table,
        active=resource.active,
        fetcher_type=map_fetcher_type(resource.fetcher_type),
        params=[map_resource_param(p) for p in resource.params]
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


@strawberry.type
class Query:
    @strawberry.field
    def fetcher_types(self) -> List[FetcherTypeType]:
        """Lista todos los tipos de fetchers disponibles"""
        db = get_db()
        try:
            fetcher_types = db.query(FetcherType).all()
            return [map_fetcher_type(ft) for ft in fetcher_types]
        finally:
            db.close()

    @strawberry.field
    def fetcher_type(self, id: str) -> Optional[FetcherTypeType]:
        """Obtiene un FetcherType por ID"""
        db = get_db()
        try:
            ft = db.query(FetcherType).filter(FetcherType.id == id).first()
            return map_fetcher_type(ft) if ft else None
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
            # Ejecutar el fetcher
            data = FetcherManager.run(db, id)

            # Limitar los datos de muestra
            if isinstance(data, list):
                return data[:limit]
            return data
        finally:
            db.close()
