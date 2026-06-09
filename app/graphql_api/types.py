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
    # Nullable: la columna lo es y la factory tiene fallback para filas sin
    # class_path. Declararlo no-nulo tumbaba el listado (seed de arranque y
    # GetFetchers del UI) en cuanto existía una fila así.
    class_path: Optional[str] = strawberry.field(default=None, name="classPath")
    # Campo calculado: la especie tiene implementación importable (vs. matriculada
    # de forma aspiracional). Resuelto por FetcherFactory.is_implemented (cacheado).
    implemented: bool = False
    modos: List[str] = strawberry.field(default_factory=lambda: ["extraer"])
    description: Optional[str] = None
    params_def: List["FetcherParamType"] = strawberry.field(default_factory=list)
    name: str = strawberry.field(name="name")
    resources: Optional[List["ResourceType"]] = None
    deleted_at: Optional[datetime] = strawberry.field(default=None, name="deletedAt")
    created_at: Optional[datetime] = strawberry.field(default=None, name="createdAt")
    preset_params: Optional[strawberry.scalars.JSON] = strawberry.field(default=None, name="presetParams")
    presets: Optional[List["PresetType"]] = None


@strawberry.type
class PresetType:
    """Variante de una especie de fetcher: implementación concreta con nombre,
    elegida por recurso. No es una entrada del catálogo."""
    id: str
    code: str
    description: Optional[str] = None
    params: Optional[strawberry.scalars.JSON] = None
    # Candado selectivo (§6c): parámetros cuyo valor no es pisable por el recurso
    locked_params: Optional[strawberry.scalars.JSON] = None

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
    hint: Optional[str] = None
    help_md: Optional[str] = strawberry.field(default=None, name="helpMd")
    visible_when: Optional[strawberry.scalars.JSON] = strawberry.field(default=None, name="visibleWhen")


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
    preset_id: Optional[str] = strawberry.field(default=None, name="presetId")
    genera_colecciones: bool = strawberry.field(default=False, name="generaColecciones")


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
    preset_id: Optional[str] = strawberry.field(default=None, name="presetId")
    genera_colecciones: Optional[bool] = strawberry.field(default=None, name="generaColecciones")


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
    hint: Optional[str] = None
    help_md: Optional[str] = strawberry.field(default=None, name="helpMd")
    visible_when: Optional[strawberry.scalars.JSON] = strawberry.field(default=None, name="visibleWhen")


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
    hint: Optional[str] = None
    help_md: Optional[str] = strawberry.field(default=None, name="helpMd")
    visible_when: Optional[strawberry.scalars.JSON] = strawberry.field(default=None, name="visibleWhen")


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
    execution_id: Optional[str] = strawberry.field(default=None, name="executionId")
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
    kind: str = "extraccion"
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
class ResourceSubscriptionType:
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
    parent_resource_id: Optional[str] = strawberry.field(default=None, name="parentResourceId")
    auto_generated: bool = strawberry.field(default=False, name="autoGenerated")
    genera_colecciones: bool = strawberry.field(default=False, name="generaColecciones")
    # Procedencia del recurso: ui | manifest | seed. Junto con autoGenerated
    # permite distinguir manifiesto / seed / descubierto-por-crawler / manual.
    origin: Optional[str] = None
    created_by_kind: Optional[str] = strawberry.field(default=None, name="createdByKind")
    subscriber_count: int = strawberry.field(default=0, name="subscriberCount")
    subscriber_apps: Optional[List[str]] = strawberry.field(default=None, name="subscriberApps")
    children: Optional[List["ResourceType"]] = strawberry.field(default=None)
    preset: Optional["PresetType"] = strawberry.field(default=None)
    last_tested_at: Optional[datetime] = strawberry.field(default=None, name="lastTestedAt")
    es_coleccion: bool = strawberry.field(default=False, name="esColeccion")
    estado_aprobacion: str = strawberry.field(default="aprobado", name="estadoAprobacion")
    motivo_rechazo: Optional[str] = strawberry.field(default=None, name="motivoRechazo")
    candidatos_pendientes: int = strawberry.field(default=0, name="candidatosPendientes")
    miembros: int = strawberry.field(default=0, name="miembros")
    ultimo_descubrimiento: Optional[datetime] = strawberry.field(default=None, name="ultimoDescubrimiento")


@strawberry.type
class ResourceCandidateType:
    """Propuesta de agrupación inferida por el GroupingInferer."""
    id: str
    execution_id: Optional[str] = strawberry.field(default=None, name="executionId")
    crawler_resource_id: str = strawberry.field(name="crawlerResourceId")
    path_template: str = strawberry.field(name="pathTemplate")
    dimensions: strawberry.scalars.JSON
    matched_urls: strawberry.scalars.JSON = strawberry.field(name="matchedUrls")
    file_types: strawberry.scalars.JSON = strawberry.field(name="fileTypes")
    suggested_name: Optional[str] = strawberry.field(default=None, name="suggestedName")
    confidence: Optional[float] = None
    status: str
    promoted_resource_id: Optional[str] = strawberry.field(default=None, name="promotedResourceId")
    merged_into_id: Optional[str] = strawberry.field(default=None, name="mergedIntoId")
    split_from_id: Optional[str] = strawberry.field(default=None, name="splitFromId")
    detected_at: Optional[datetime] = strawberry.field(default=None, name="detectedAt")
    reviewed_at: Optional[datetime] = strawberry.field(default=None, name="reviewedAt")
    reviewed_by: Optional[str] = strawberry.field(default=None, name="reviewedBy")
    deleted_at: Optional[datetime] = strawberry.field(default=None, name="deletedAt")


@strawberry.input
class PromoverRamaInput:
    """Promueve una rama entera del árbol del crawler a recurso(s) fundidos.

    Funde las hojas de la rama derivando como columnas los segmentos que varían.
    Concern de ODM puro: no hay nada de mapeo a destinos (CKAN u otros)."""
    crawler_resource_id: strawberry.ID = strawberry.field(name="crawlerResourceId")
    rama_path: str = strawberry.field(name="ramaPath")
    variant: Optional[str] = None
    name: Optional[str] = None
    enable_load: Optional[bool] = strawberry.field(default=False, name="enableLoad")
    schedule: Optional[str] = None
    # Por defecto solo promueve las fusiones con patrón de serie ({*}); con esto
    # se incluyen también las hojas sueltas (ficheros individuales).
    incluir_no_series: Optional[bool] = strawberry.field(default=False, name="incluirNoSeries")


@strawberry.input
class PromoteCandidateInput:
    """Datos editables al promover una candidata a Resource hijo."""
    name: str
    target_table: str = strawberry.field(name="targetTable")
    schedule: Optional[str] = None
    enable_load: Optional[bool] = strawberry.field(default=False, name="enableLoad")
    load_mode: Optional[str] = strawberry.field(default="upsert", name="loadMode")
    # Variante (FetcherPreset.code) con la que nace el hijo: 'Censo documental',
    # 'Extracción de datos', 'Extracción con receta'... Se resuelve bajo la
    # especie del crawler padre. None ⇒ sin variante (comportamiento histórico).
    variant: Optional[str] = None




# ── §12 Alta de aplicaciones (M2M): solicitud → aprobación → token ──────────

@strawberry.type
class SolicitudIngresoType:
    id: str
    nombre: str
    contacto: Optional[str] = None
    proposito: Optional[str] = None
    estado: str = "pendiente"
    motivo: Optional[str] = None
    created_at: Optional[datetime] = strawberry.field(default=None, name="createdAt")
    resuelta_at: Optional[datetime] = strawberry.field(default=None, name="resueltaAt")
    usuario_id: Optional[str] = strawberry.field(default=None, name="usuarioId")


@strawberry.input
class CrearSolicitudIngresoInput:
    """Solicitud self-service: una aplicación pide el alta en ODM."""
    nombre: str
    contacto: Optional[str] = None
    proposito: Optional[str] = None
    callback_url: Optional[str] = None      # callbackUrl: push de la resolución
    callback_secret: Optional[str] = None   # callbackSecret: firma del webhook


@strawberry.type
class AprobarSolicitudResult:
    """Resultado de aprobar una solicitud. El token en claro se entrega UNA sola
    vez aquí (display-once); en reposo solo queda su hash."""
    solicitud: SolicitudIngresoType
    usuario_id: str = strawberry.field(name="usuarioId")
    username: str
    token: str            # secreto en claro — mostrar una vez y no volver a pedir
    token_prefix: str = strawberry.field(name="tokenPrefix")


# ── §12 Gestión de credenciales de aplicaciones (cuentas de servicio) ───────

@strawberry.type
class ServiceTokenType:
    id: str
    label: Optional[str] = None
    prefix: str = ""
    last_used_at: Optional[datetime] = strawberry.field(default=None, name="lastUsedAt")
    expires_at: Optional[datetime] = strawberry.field(default=None, name="expiresAt")
    revoked_at: Optional[datetime] = strawberry.field(default=None, name="revokedAt")
    activo: bool = True   # no revocado y no expirado


@strawberry.type
class AplicacionM2MType:
    """Aplicación aprobada: el principal (Usuario tipo='aplicacion') y sus tokens."""
    usuario_id: str = strawberry.field(name="usuarioId")
    username: str
    email: Optional[str] = None
    is_active: bool = strawberry.field(default=True, name="isActive")
    tokens: List[ServiceTokenType] = strawberry.field(default_factory=list)


@strawberry.type
class TokenEmitidoResult:
    """Token recién emitido/rotado. El secreto en claro se entrega UNA vez."""
    token_id: str = strawberry.field(name="tokenId")
    usuario_id: str = strawberry.field(name="usuarioId")
    prefix: str
    token: str   # secreto en claro — display-once


@strawberry.type
class TaxonomiaNodoType:
    """Nodo del árbol de ramas derivado al vuelo de los candidatos de un crawler.

    Vista plana: el cliente reconstruye el árbol por `path`/`parent`. Cada nodo
    con `candidatoIds` no vacío es promovible como rama."""
    path: str
    label: str
    parent: Optional[str] = None
    depth: int = 0
    num_candidatos: int = strawberry.field(default=0, name="numCandidatos")
    num_directos: int = strawberry.field(default=0, name="numDirectos")
    num_urls: int = strawberry.field(default=0, name="numUrls")
    formatos: Optional[strawberry.scalars.JSON] = None
    dimensiones: List[str] = strawberry.field(default_factory=list)
    candidato_ids: List[str] = strawberry.field(default_factory=list, name="candidatoIds")
