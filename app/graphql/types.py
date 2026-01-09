"""
Tipos GraphQL para la API.
"""
import strawberry
from typing import Optional, List
from datetime import datetime


@strawberry.type
class FetcherTypeType:
    """Tipo de fetcher disponible (REST, SOAP, CSV, etc.)"""
    id: str
    code: str
    class_path: str
    description: Optional[str] = None
    params_def: Optional[strawberry.scalars.JSON] = None


@strawberry.type
class TypeFetcherParamType:
    """Parámetro requerido por un tipo de fetcher"""
    id: str
    param_name: str
    required: bool
    data_type: str


@strawberry.type
class ResourceParamType:
    """Parámetro configurado para un resource"""
    id: str
    key: str
    value: str


@strawberry.type
class ResourceType:
    """Fuente de datos configurada"""
    id: str
    name: str
    publisher: str
    target_table: str
    active: bool
    fetcher_type: FetcherTypeType
    params: List[ResourceParamType]


@strawberry.type
class ApplicationType:
    """Aplicación suscrita al sistema"""
    id: str
    name: str
    description: Optional[str] = None
    models_path: str
    subscribed_projects: List[str]
    active: bool


@strawberry.input
class ResourceParamInput:
    """Input para parámetros de Resource"""
    key: str
    value: str


@strawberry.input
class CreateResourceInput:
    """Input para crear un nuevo Resource"""
    name: str
    publisher: str
    fetcher_type_id: str
    params: List[ResourceParamInput]
    active: bool = True
    target_table: Optional[str] = None


@strawberry.input
class UpdateResourceInput:
    """Input para actualizar un Resource"""
    name: Optional[str] = None
    publisher: Optional[str] = None
    target_table: Optional[str] = None
    fetcher_type_id: Optional[str] = None
    params: Optional[List[ResourceParamInput]] = None
    active: Optional[bool] = None


@strawberry.input
class CreateFetcherTypeInput:
    """Input para crear un nuevo FetcherType"""
    code: str
    class_path: str
    description: Optional[str] = None


@strawberry.input
class UpdateFetcherTypeInput:
    """Input para actualizar un FetcherType"""
    code: Optional[str] = None
    class_path: Optional[str] = None
    description: Optional[str] = None


@strawberry.type
class ExecutionResult:
    """Resultado de ejecutar un Resource"""
    success: bool
    message: str
    resource_id: Optional[str] = None
    sample_data: Optional[strawberry.scalars.JSON] = None


@strawberry.type
class FieldMetadataType:
    """Metadata de un campo para tooltips"""
    id: str
    table_name: str
    field_name: str
    label: Optional[str] = None
    help_text: Optional[str] = None
    placeholder: Optional[str] = None


@strawberry.type
class ResourceExecutionType:
    """Audit trail de ejecuciones de Resources"""
    id: str
    resource_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    total_records: Optional[int] = None
    records_loaded: Optional[int] = None
    staging_path: Optional[str] = None
    error_message: Optional[str] = None


@strawberry.type
class ArtifactType:
    """Versioned package de datos extraídos"""
    id: str
    resource_id: str
    execution_id: Optional[str] = None
    version: str
    major_version: int
    minor_version: int
    patch_version: int
    schema_json: strawberry.scalars.JSON
    data_path: str
    record_count: Optional[int] = None
    checksum: Optional[str] = None
    created_at: datetime
    download_urls: strawberry.scalars.JSON


@strawberry.type
class ArtifactSubscriptionType:
    """Suscripción pasiva de Application a Resource"""
    id: str
    application_id: str
    resource_id: str
    pinned_version: Optional[str] = None
    auto_upgrade: str
    current_version: Optional[str] = None
    notified_at: Optional[datetime] = None


@strawberry.type
class ApplicationNotificationType:
    """Log de webhooks enviados"""
    id: str
    application_id: str
    artifact_id: Optional[str] = None
    sent_at: datetime
    status_code: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None
