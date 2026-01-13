"""
Tipos GraphQL para la API.
"""
import strawberry
from typing import Optional, List
from datetime import datetime


@strawberry.type
class TypeFetcherParamType:
    """Parámetro requerido por un tipo de fetcher"""
    id: str
    param_name: str = strawberry.field(name="paramName")
    required: bool
    data_type: str = strawberry.field(name="dataType")
    default_value: Optional[strawberry.scalars.JSON] = strawberry.field(default=None, name="defaultValue")
    enum_values: Optional[List[str]] = strawberry.field(default=None, name="enumValues")


@strawberry.type
class ResourceParamType:
    """Parámetro configurado para un resource"""
    id: str
    key: str
    value: str


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
    fetcher_id: str = strawberry.field(name="fetcherId")
    params: List[ResourceParamInput]
    active: bool = True
    target_table: Optional[str] = strawberry.field(default=None, name="targetTable")


@strawberry.input
class UpdateResourceInput:
    """Input para actualizar un Resource"""
    name: Optional[str] = None
    publisher: Optional[str] = None
    target_table: Optional[str] = strawberry.field(default=None, name="targetTable")
    fetcher_id: Optional[str] = strawberry.field(default=None, name="fetcherId")
    params: Optional[List[ResourceParamInput]] = None
    active: Optional[bool] = None


@strawberry.input
class CreateFetcherInput:
    """Input para crear un nuevo Fetcher"""
    name: str
    class_path: str = strawberry.field(name="classPath")
    description: Optional[str] = None


@strawberry.input
class UpdateFetcherInput:
    """Input para actualizar un Fetcher"""
    name: Optional[str] = None
    class_path: Optional[str] = strawberry.field(default=None, name="classPath")
    description: Optional[str] = None


@strawberry.input
class CreateTypeFetcherParamInput:
    """Input para crear parámetro de fetcher"""
    fetcher_id: str = strawberry.field(name="fetcherId")
    param_name: str = strawberry.field(name="paramName")
    required: bool = True
    data_type: str = strawberry.field(name="dataType")
    default_value: Optional[strawberry.scalars.JSON] = strawberry.field(default=None, name="defaultValue")
    enum_values: Optional[List[str]] = strawberry.field(default=None, name="enumValues")


@strawberry.input
class UpdateTypeFetcherParamInput:
    """Input para actualizar parámetro de fetcher"""
    param_name: Optional[str] = strawberry.field(default=None, name="paramName")
    required: Optional[bool] = None
    data_type: Optional[str] = strawberry.field(default=None, name="dataType")
    default_value: Optional[strawberry.scalars.JSON] = strawberry.field(default=None, name="defaultValue")
    enum_values: Optional[List[str]] = strawberry.field(default=None, name="enumValues")


@strawberry.type
class ApplicationType:
    """Aplicación suscrita al sistema"""
    id: str
    name: str
    description: Optional[str] = None
    models_path: str = strawberry.field(name="modelsPath")
    subscribed_projects: List[str] = strawberry.field(name="subscribedProjects")
    active: bool


@strawberry.type
class ExecutionResult:
    """Resultado de ejecutar un Resource"""
    success: bool
    message: str
    resource_id: Optional[str] = strawberry.field(default=None, name="resourceId")
    sample_data: Optional[strawberry.scalars.JSON] = strawberry.field(default=None, name="sampleData")


@strawberry.type
class FieldMetadataType:
    """Metadata de un campo para tooltips"""
    id: str
    table_name: str = strawberry.field(name="tableName")
    field_name: str = strawberry.field(name="fieldName")
    label: Optional[str] = None
    help_text: Optional[str] = strawberry.field(default=None, name="helpText")
    placeholder: Optional[str] = None


@strawberry.type
class ResourceExecutionType:
    """Audit trail de ejecuciones de Resources"""
    id: str
    resource_id: str = strawberry.field(name="resourceId")
    started_at: datetime = strawberry.field(name="startedAt")
    completed_at: Optional[datetime] = strawberry.field(default=None, name="completedAt")
    status: str
    total_records: Optional[int] = strawberry.field(default=None, name="totalRecords")
    records_loaded: Optional[int] = strawberry.field(default=None, name="recordsLoaded")
    staging_path: Optional[str] = strawberry.field(default=None, name="stagingPath")
    error_message: Optional[str] = strawberry.field(default=None, name="errorMessage")


@strawberry.type
class ArtifactType:
    """Versioned package de datos extraídos"""
    id: str
    resource_id: str = strawberry.field(name="resourceId")
    execution_id: Optional[str] = strawberry.field(default=None, name="executionId")
    version: str
    major_version: int = strawberry.field(name="majorVersion")
    minor_version: int = strawberry.field(name="minorVersion")
    patch_version: int = strawberry.field(name="patchVersion")
    schema_json: strawberry.scalars.JSON = strawberry.field(name="schemaJson")
    data_path: str = strawberry.field(name="dataPath")
    record_count: Optional[int] = strawberry.field(default=None, name="recordCount")
    checksum: Optional[str] = None
    created_at: datetime = strawberry.field(name="createdAt")
    download_urls: strawberry.scalars.JSON = strawberry.field(name="downloadUrls")


@strawberry.type
class ArtifactSubscriptionType:
    """Suscripción pasiva de Application a Resource"""
    id: str
    application_id: str = strawberry.field(name="applicationId")
    resource_id: str = strawberry.field(name="resourceId")
    pinned_version: Optional[str] = strawberry.field(default=None, name="pinnedVersion")
    auto_upgrade: str = strawberry.field(name="autoUpgrade")
    current_version: Optional[str] = strawberry.field(default=None, name="currentVersion")
    notified_at: Optional[datetime] = strawberry.field(default=None, name="notifiedAt")


@strawberry.type
class ApplicationNotificationType:
    """Log de webhooks enviados"""
    id: str
    application_id: str = strawberry.field(name="applicationId")
    artifact_id: Optional[str] = strawberry.field(default=None, name="artifactId")
    sent_at: datetime = strawberry.field(name="sentAt")
    status_code: Optional[int] = strawberry.field(default=None, name="statusCode")
    response_body: Optional[str] = strawberry.field(default=None, name="responseBody")
    error_message: Optional[str] = strawberry.field(default=None, name="errorMessage")


@strawberry.type
class ResourceType:
    """Fuente de datos configurada"""
    id: str
    name: str
    publisher: str
    target_table: str = strawberry.field(name="targetTable")
    active: bool
    fetcher: "Fetcher"
    params: List[ResourceParamType]


@strawberry.type
class Fetcher:
    """Fetcher disponible (REST API, HTML Forms, etc.)"""
    id: str
    code: str
    name: str
    class_path: Optional[str] = strawberry.field(default=None, name="classPath")
    description: Optional[str] = None
    params_def: Optional[List[TypeFetcherParamType]] = strawberry.field(default=None, name="paramsDef")
    resources: Optional[List[ResourceType]] = None

