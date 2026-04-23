"""
Tipos GraphQL para la API.
"""
import strawberry
from typing import Optional, List
from datetime import datetime

@strawberry.type
class FetcherType:
    """Tipo de fetcher"""
    id: str
    code: str
    class_path: str = strawberry.field(name="classPath")
    description: Optional[str] = None
    params_def: List["FetcherParamType"] = strawberry.field(default_factory=list)
    name: str = strawberry.field(name="name")
    resources: Optional[List["ResourceType"]] = None
    deleted_at: Optional[datetime] = strawberry.field(default=None, name="deletedAt")

@strawberry.type
class FetcherParamType:
    """Parámetro requerido por un tipo de fetcher"""
    id: str
    param_name: str = strawberry.field(name="paramName")
    required: bool
    data_type: str = strawberry.field(name="dataType")
    default_value: Optional[strawberry.scalars.JSON] = strawberry.field(default=None, name="defaultValue")
    enum_values: Optional[strawberry.scalars.JSON] = strawberry.field(default=None, name="enumValues")
    description: Optional[str] = None
    group: Optional[str] = None


@strawberry.type
class ResourceParamType:
    """Parámetro configurado para un resource"""
    id: str
    key: str
    value: str
    is_external: bool = strawberry.field(default=False, name="isExternal")


@strawberry.input
class ResourceParamInput:
    """Input para parámetros de Resource"""
    key: str
    value: str
    is_external: bool = strawberry.field(default=False, name="isExternal")


@strawberry.input
class CreateResourceInput:
    """Input para crear un nuevo Resource"""
    name: str
    description: Optional[str] = None
    fetcher_id: str = strawberry.field(name="fetcherId")
    params: List[ResourceParamInput]
    active: bool = True
    publisher: Optional[str] = None
    publisher_id: Optional[str] = strawberry.field(default=None, name="publisherId")
    target_table: Optional[str] = strawberry.field(default=None, name="targetTable")
    schedule: Optional[str] = None


@strawberry.input
class UpdateResourceInput:
    """Input para actualizar un Resource"""
    name: Optional[str] = None
    description: Optional[str] = None
    publisher: Optional[str] = None
    publisher_id: Optional[str] = strawberry.field(default=None, name="publisherId")
    target_table: Optional[str] = strawberry.field(default=None, name="targetTable")
    fetcher_id: Optional[str] = strawberry.field(default=None, name="fetcherId")
    params: Optional[List[ResourceParamInput]] = None
    active: Optional[bool] = None
    schedule: Optional[str] = strawberry.field(default=None, name="schedule")


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
    enum_values: Optional[strawberry.scalars.JSON] = strawberry.field(default=None, name="enumValues")
    description: Optional[str] = None
    group: Optional[str] = None


@strawberry.input
class UpdateTypeFetcherParamInput:
    """Input para actualizar parámetro de fetcher"""
    param_name: Optional[str] = strawberry.field(default=None, name="paramName")
    required: Optional[bool] = None
    data_type: Optional[str] = strawberry.field(default=None, name="dataType")
    default_value: Optional[strawberry.scalars.JSON] = strawberry.field(default=None, name="defaultValue")
    enum_values: Optional[strawberry.scalars.JSON] = strawberry.field(default=None, name="enumValues")
    description: Optional[str] = None
    group: Optional[str] = None


@strawberry.type
class ApplicationType:
    """Aplicación suscrita al sistema"""
    id: str
    name: str
    description: Optional[str] = None
    models_path: Optional[str] = strawberry.field(default=None, name="modelsPath")
    subscribed_projects: List[str] = strawberry.field(name="subscribedProjects")
    active: bool
    webhook_url: Optional[str] = strawberry.field(default=None, name="webhookUrl")
    consumption_mode: str = strawberry.field(default="webhook", name="consumptionMode")
    deleted_at: Optional[datetime] = strawberry.field(default=None, name="deletedAt")

@strawberry.input
class CreateApplicationInput:
    name: str
    description: Optional[str] = None
    subscribed_projects: List[str] = strawberry.field(default_factory=list, name="subscribedProjects")
    active: bool = True
    consumption_mode: str = strawberry.field(default="webhook", name="consumptionMode")
    webhook_url: Optional[str] = strawberry.field(default=None, name="webhookUrl")

@strawberry.input
class UpdateApplicationInput:
    name: Optional[str] = None
    description: Optional[str] = None
    subscribed_projects: Optional[List[str]] = strawberry.field(default=None, name="subscribedProjects")
    active: Optional[bool] = None
    consumption_mode: Optional[str] = strawberry.field(default=None, name="consumptionMode")
    webhook_url: Optional[str] = strawberry.field(default=None, name="webhookUrl")

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
    resource_name: Optional[str] = strawberry.field(default=None, name="resourceName")
    started_at: datetime = strawberry.field(name="startedAt")
    completed_at: Optional[datetime] = strawberry.field(default=None, name="completedAt")
    status: str
    total_records: Optional[int] = strawberry.field(default=None, name="totalRecords")
    records_loaded: Optional[int] = strawberry.field(default=None, name="recordsLoaded")
    staging_path: Optional[str] = strawberry.field(default=None, name="stagingPath")
    error_message: Optional[str] = strawberry.field(default=None, name="errorMessage")
    execution_params: Optional[strawberry.scalars.JSON] = strawberry.field(default=None, name="executionParams")
    pause_requested: bool = strawberry.field(default=False, name="pauseRequested")
    active_seconds: Optional[int] = strawberry.field(default=None, name="activeSeconds")
    deleted_at: Optional[datetime] = strawberry.field(default=None, name="deletedAt")


@strawberry.type
class DatasetType:
    """Versioned package de datos extraídos"""
    id: str
    resource_id: str = strawberry.field(name="resourceId")
    execution_id: Optional[str] = strawberry.field(default=None, name="executionId")
    version: str
    label: Optional[str] = None
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
class DatasetSubscriptionType:
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
    dataset_id: Optional[str] = strawberry.field(default=None, name="datasetId")
    sent_at: datetime = strawberry.field(name="sentAt")
    status_code: Optional[int] = strawberry.field(default=None, name="statusCode")
    response_body: Optional[str] = strawberry.field(default=None, name="responseBody")
    error_message: Optional[str] = strawberry.field(default=None, name="errorMessage")


@strawberry.type
class AppConfigType:
    """Global application setting"""
    key: str
    value: strawberry.scalars.JSON
    description: Optional[str] = None
    updated_at: Optional[datetime] = strawberry.field(default=None, name="updatedAt")

@strawberry.input
class SetConfigInput:
    key: str
    value: strawberry.scalars.JSON


@strawberry.type
class DerivedDatasetConfigType:
    """Config for a derived/catalog dataset extracted as a side-product of a resource execution."""
    id: str
    source_resource_id: str = strawberry.field(name="sourceResourceId")
    target_name: str = strawberry.field(name="targetName")
    key_field: str = strawberry.field(name="keyField")
    extract_fields: strawberry.scalars.JSON = strawberry.field(name="extractFields")
    merge_strategy: str = strawberry.field(name="mergeStrategy")
    enabled: bool
    description: Optional[str] = None
    created_at: datetime = strawberry.field(name="createdAt")
    entry_count: Optional[int] = strawberry.field(default=None, name="entryCount")


@strawberry.input
class CreateDerivedDatasetConfigInput:
    source_resource_id: str = strawberry.field(name="sourceResourceId")
    target_name: str = strawberry.field(name="targetName")
    key_field: str = strawberry.field(name="keyField")
    extract_fields: strawberry.scalars.JSON = strawberry.field(name="extractFields")
    merge_strategy: str = strawberry.field(default="upsert", name="mergeStrategy")
    enabled: bool = True
    description: Optional[str] = None


@strawberry.input
class UpdateDerivedDatasetConfigInput:
    target_name: Optional[str] = strawberry.field(default=None, name="targetName")
    key_field: Optional[str] = strawberry.field(default=None, name="keyField")
    extract_fields: Optional[strawberry.scalars.JSON] = strawberry.field(default=None, name="extractFields")
    merge_strategy: Optional[str] = strawberry.field(default=None, name="mergeStrategy")
    enabled: Optional[bool] = None
    description: Optional[str] = None


@strawberry.type
class PublisherType:
    """Organismo o portal publicador de datos abiertos"""
    id: str
    nombre: str
    acronimo: Optional[str] = None
    nivel: str
    pais: str
    comunidad_autonoma: Optional[str] = strawberry.field(default=None, name="comunidadAutonoma")
    provincia: Optional[str] = None
    municipio: Optional[str] = None
    portal_url: Optional[str] = strawberry.field(default=None, name="portalUrl")
    email: Optional[str] = None
    telefono: Optional[str] = None
    created_at: Optional[datetime] = strawberry.field(default=None, name="createdAt")
    deleted_at: Optional[datetime] = strawberry.field(default=None, name="deletedAt")


@strawberry.input
class CreatePublisherInput:
    nombre: str
    nivel: str
    pais: str = "España"
    acronimo: Optional[str] = None
    comunidad_autonoma: Optional[str] = strawberry.field(default=None, name="comunidadAutonoma")
    provincia: Optional[str] = None
    municipio: Optional[str] = None
    portal_url: Optional[str] = strawberry.field(default=None, name="portalUrl")
    email: Optional[str] = None
    telefono: Optional[str] = None


@strawberry.input
class UpdatePublisherInput:
    nombre: Optional[str] = None
    nivel: Optional[str] = None
    pais: Optional[str] = None
    acronimo: Optional[str] = None
    comunidad_autonoma: Optional[str] = strawberry.field(default=None, name="comunidadAutonoma")
    provincia: Optional[str] = None
    municipio: Optional[str] = None
    portal_url: Optional[str] = strawberry.field(default=None, name="portalUrl")
    email: Optional[str] = None
    telefono: Optional[str] = None


@strawberry.type
class ResourceType:
    """Fuente de datos configurada"""
    id: str
    name: str
    description: Optional[str] = None
    publisher: Optional[str] = None
    publisher_id: Optional[str] = strawberry.field(default=None, name="publisherId")
    publisher_obj: Optional[PublisherType] = strawberry.field(default=None, name="publisherObj")
    target_table: Optional[str] = strawberry.field(name="targetTable")
    active: bool
    schedule: Optional[str] = None
    fetcher: FetcherType
    params: List[ResourceParamType]
    created_at: Optional[datetime] = strawberry.field(default=None, name="createdAt")
    deleted_at: Optional[datetime] = strawberry.field(default=None, name="deletedAt")


