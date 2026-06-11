from uuid import uuid4
from datetime import datetime
from sqlalchemy import Column, String, Boolean, ForeignKey, Text, Integer, Float, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, declared_attr
from app.database import Base


class AuditMixin:
    """Autoría/auditoría común para los modelos de dominio.

    Aplíquese como ``class Foo(AuditMixin, Base): ...``. Registra quién y cuándo
    creó/actualizó la fila. ``created_by_id``/``updated_by_id`` referencian
    ``opendata.usuario.id`` (para aplicaciones, el usuario funcional ``svr-*``).
    ``updated_at`` se actualiza solo en cada UPDATE.
    """

    @declared_attr
    def created_at(cls):
        return Column(DateTime, default=datetime.utcnow, nullable=True)

    @declared_attr
    def updated_at(cls):
        return Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

    @declared_attr
    def created_by_id(cls):
        return Column(UUID(as_uuid=True), ForeignKey("opendata.usuario.id", ondelete="SET NULL"), nullable=True)

    @declared_attr
    def updated_by_id(cls):
        return Column(UUID(as_uuid=True), ForeignKey("opendata.usuario.id", ondelete="SET NULL"), nullable=True)


class AppConfig(AuditMixin, Base):
    """Global application settings stored as key-value pairs."""
    __tablename__ = "app_config"
    __table_args__ = {"schema": "opendata"}

    key = Column(String(100), primary_key=True)
    value = Column(JSONB, nullable=False)
    description = Column(Text, nullable=True)

class Fetcher(AuditMixin, Base):
    __tablename__ = "fetcher"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    # DB migrations renamed this column to 'name' — keep attribute `code`
    # mapped to DB column 'name' for backward compatibility in code.
    code = Column('name', String(50), unique=True, nullable=False)
    class_path = Column(String(255), nullable=True)

    @property
    def implemented(self) -> bool:
        """Campo calculado: la especie tiene implementación (su class_path o el
        fallback de su code resuelven a una clase importable)."""
        from app.fetchers.factory import FetcherFactory
        return FetcherFactory.is_implemented(self.class_path, self.code)
    description = Column(Text)
    # Bloque de parámetros preestablecidos que convierte a este fetcher en una
    # VARIANTE de su especie (class_path): aísla las peculiaridades de una familia
    # de fuentes (p. ej. el field_map CODICE) para inyectarlas en el fetcher genérico.
    preset_params = Column(JSONB, nullable=True)  # LEGACY: sustituido por FetcherPreset; se conserva como fallback transitorio

    presets = relationship("FetcherPreset", back_populates="fetcher", cascade="all, delete-orphan")
    # Capacidad declarada de la especie: qué modos de operación soporta.
    # 'extraer' (produce dataset) y/o 'descubrir' (produce candidatos → es una
    # nave nodriza de Colecciones). Lo que hace a Web Tree una Colección no es su
    # tipo, sino llevar 'descubrir' aquí — y el día que otra especie lo lleve,
    # será Colección sin tocar nada más.
    modos = Column(JSONB, nullable=False, default=lambda: ["extraer"], server_default='["extraer"]')

    @property
    def descubre(self) -> bool:
        return "descubrir" in (self.modos or [])
    deleted_at = Column(DateTime, nullable=True)

    params_def = relationship("FetcherParams", back_populates="fetcher")
    resources = relationship("Resource", back_populates="fetcher")


class FetcherParams(AuditMixin, Base):
    __tablename__ = "type_fetcher_params"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    fetcher_id = Column(UUID(as_uuid=True), ForeignKey("opendata.fetcher.id"))
    param_name = Column(String(100), nullable=False)
    required = Column(Boolean, default=True)
    data_type = Column(String(20), default="string")
    default_value = Column(JSONB, nullable=True)
    enum_values = Column(JSONB, nullable=True)
    description = Column(Text, nullable=True)
    group = Column(String(100), nullable=True)
    hint = Column(String(255), nullable=True)          # microcopy inline (1 línea)
    help_md = Column(Text, nullable=True)              # ayuda extensa (modal, markdown)
    visible_when = Column(JSONB, nullable=True)        # condición {"param":..,"in":[..]}

    fetcher = relationship("Fetcher", back_populates="params_def")


class Publisher(AuditMixin, Base):
    """Entidad publicadora de datos abiertos (organismo, portal, administración)."""
    __tablename__ = "publisher"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    nombre = Column(String(200), nullable=False)
    acronimo = Column(String(30), nullable=True)
    nivel = Column(String(30), nullable=False)  # ESTATAL | AUTONOMICO | PROVINCIAL | LOCAL | EUROPEO | INTERNACIONAL
    pais = Column(String(100), nullable=False, default="España")
    comunidad_autonoma = Column(String(100), nullable=True)
    provincia = Column(String(100), nullable=True)
    municipio = Column(String(200), nullable=True)
    portal_url = Column(String(500), nullable=True)
    email = Column(String(200), nullable=True)
    telefono = Column(String(50), nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    resources = relationship("Resource", back_populates="publisher_obj")


class ResourceCollection(AuditMixin, Base):
    """Collection organizativa de recursos.

    Una de dos naturalezas según su origen:
      - 'organizativa': carpeta creada a mano, sin raíz.
      - 'matriz': originada por un recurso matriz descubridor, que la preside
        vía ``root_resource_id``.
    Un recurso pertenece como mucho a UNA collection (Resource.resource_collection_id).
    Al borrar la collection, sus miembros quedan «sin agrupar» (FK SET NULL), nunca
    se borran.
    """
    __tablename__ = "resource_collection"
    __table_args__ = (
        UniqueConstraint("name", name="uq_resource_collection_name"),
        {"schema": "opendata"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False)
    origin = Column(String(20), default="organizativa", server_default="organizativa", nullable=False)  # organizativa | matriz
    # Para las de origen 'matriz': el recurso que la preside. Si se borra la
    # matriz, su collection se va con ella (y sus miembros quedan sin agrupar).
    root_resource_id = Column(UUID(as_uuid=True), ForeignKey("opendata.resource.id", ondelete="CASCADE"), nullable=True)


class Resource(AuditMixin, Base):
    __tablename__ = "resource"
    __table_args__ = (
        UniqueConstraint("params_hash", name="uq_resource_params_hash"),
        {"schema": "opendata"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    publisher = Column(String(200), nullable=True)   # texto libre (legado / fallback)
    publisher_id = Column(UUID(as_uuid=True), ForeignKey("opendata.publisher.id"), nullable=True)
    target_table = Column(String(100), nullable=True)
    fetcher_id = Column(UUID(as_uuid=True), ForeignKey("opendata.fetcher.id"))
    active = Column(Boolean, default=True)
    schedule = Column(String(100), nullable=True)  # cron expression, e.g. "0 2 * * *"

    # New fields for dataset system
    enable_load = Column(Boolean, default=False)
    load_mode = Column(String(20), default="replace")

    parent_resource_id = Column(UUID(as_uuid=True), ForeignKey("opendata.resource.id", ondelete="SET NULL"), nullable=True)
    # Collection organizativa a la que pertenece (carpeta). Nullable = «sin agrupar».
    # Al borrar la collection, este campo vuelve a NULL (no se borra el recurso).
    resource_collection_id = Column(UUID(as_uuid=True), ForeignKey("opendata.resource_collection.id", ondelete="SET NULL"), nullable=True)
    auto_generated = Column(Boolean, default=False, nullable=False)
    # Rol del recurso frente a un fetcher capaz de descubrir (p. ej. Web Tree):
    # marca si ESTE recurso actúa como nave nodriza (descubre candidatos y los
    # promueve) o si solo extrae un dato concreto. Capacidad (fetcher.descubre)
    # ≠ intención: un mismo fetcher sirve para ambas. Solo las marcadas figuran
    # como Collection. Default False: un Web Tree extrae salvo que se cualifique.
    genera_colecciones = Column(Boolean, default=False, server_default="false", nullable=False)

    # Perfil (preset) de la especie aplicado a este recurso. La particularización
    # vive en el recurso, no en el catálogo de fetchers.
    preset_id = Column(UUID(as_uuid=True), ForeignKey("opendata.fetcher_preset.id", ondelete="SET NULL"), nullable=True)

    # Ciclo de vida / caché (docs/diseno_ciclo_vida_datasets.md)
    rederivable = Column(Boolean, default=True, nullable=False)
    coste_rederivacion = Column(String(10), default="medio", nullable=False)  # bajo|medio|alto
    retencion_permanente = Column(Boolean, default=False, nullable=False)
    retencion_ttl_dias = Column(Integer, nullable=True)
    retencion_min_versiones = Column(Integer, default=1, nullable=False)
    prioridad_base = Column(Integer, default=0, nullable=False)

    # Versionado y procedencia de la definición (manifiesto canónico).
    manifest_version = Column(Integer, default=1, nullable=False)
    manifest_hash = Column(String(64), nullable=True)       # hash del manifiesto canónico actual
    last_synced_hash = Column(String(64), nullable=True)    # base común para detección de conflictos
    origin = Column(String(20), default="ui", nullable=False)  # ui | manifest | seed
    source_status = Column(String(20), default="ok", nullable=False)  # ok | baja (salud del origen)
    # §11 Gobernanza de propuestas: un recurso creado por una aplicación nace
    # 'pendiente' y no se ejecuta hasta que un admin lo aprueba; lo creado por
    # humanos con permiso nace 'aprobado'. 'rechazado' conserva el motivo.
    estado_aprobacion = Column(String(20), default="aprobado", server_default="aprobado", nullable=False)
    motivo_rechazo = Column(Text, nullable=True)
    # Última vez que el recurso fue probado desde el UI (preview), con éxito o no.
    last_tested_at = Column(DateTime, nullable=True)

    # Identidad por contenido (huella de params; distinta de manifest_hash).
    params_hash = Column(String(64), nullable=True, index=True)  # app/core/huella.py

    # created_at / created_by_id / updated_at / updated_by_id provienen de AuditMixin.
    deleted_at = Column(DateTime, nullable=True)

    fetcher = relationship("Fetcher", back_populates="resources")
    preset = relationship("FetcherPreset", back_populates="resources")
    publisher_obj = relationship("Publisher", back_populates="resources")
    params = relationship("ResourceParam", back_populates="resource", cascade="all, delete-orphan")
    executions = relationship("ResourceExecution", back_populates="resource")
    datasets = relationship("Dataset", back_populates="resource")
    derived_configs = relationship("DerivedDatasetConfig", back_populates="source_resource", cascade="all, delete-orphan")
    children = relationship("Resource", foreign_keys=[parent_resource_id], lazy="dynamic")
    # Linaje de derivados (especie CruceDatasets y futuros): recursos de los que
    # este recurso depende como fuente, y derivados que dependen de este.
    dependencies = relationship("ResourceDependency", foreign_keys="ResourceDependency.derived_resource_id",
                                cascade="all, delete-orphan", lazy="dynamic")
    dependents = relationship("ResourceDependency", foreign_keys="ResourceDependency.source_resource_id",
                              lazy="dynamic", overlaps="dependencies")

    @property
    def es_coleccion(self) -> bool:
        """Nave nodriza: recurso CUALIFICADO como generador de colecciones.
        Requiere capacidad (su fetcher declara 'descubrir'), ser recurso-madre
        (sin padre) e INTENCIÓN explícita (genera_colecciones). Las Colecciones
        descubren candidatos y los promueven; un Web Tree no cualificado solo
        extrae su dato, aunque su fetcher fuese capaz de descubrir."""
        return bool(self.fetcher and self.fetcher.descubre
                    and self.parent_resource_id is None
                    and self.genera_colecciones)


class DatasetLease(AuditMixin, Base):
    """Arrendamiento de un dataset: un titular (proceso/aplicación o usuario) pide un
    recurso con una retención; ODM concede un plazo y lo conserva mientras el lease
    siga activo. Reference counting + liberación anticipada. Ver
    docs/diseno_ciclo_vida_datasets.md."""
    __tablename__ = "dataset_lease"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    resource_id = Column(UUID(as_uuid=True), ForeignKey("opendata.resource.id", ondelete="CASCADE"), nullable=False)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("opendata.dataset.id", ondelete="SET NULL"), nullable=True)
    titular_tipo = Column(String(20), nullable=False)   # usuario | application
    titular_id = Column(UUID(as_uuid=True), nullable=True)
    email_contacto = Column(String(255), nullable=True)
    retencion_solicitada_dias = Column(Integer, nullable=True)
    permanente = Column(Boolean, default=False, nullable=False)
    concedido_hasta = Column(DateTime, nullable=True)
    estado = Column(String(20), default="activo", nullable=False)  # activo | liberado | expirado
    released_at = Column(DateTime, nullable=True)

    resource = relationship("Resource")
    dataset = relationship("Dataset")


class FetcherPreset(AuditMixin, Base):
    """Perfil (preset) de una especie de fetcher: bloque de parámetros con nombre
    que particulariza la especie para una familia de fuentes (p. ej. 'PLACSP
    CODICE' sobre 'Feeds ATOM/RSS'). Vive BAJO la especie y solo se materializa en
    los recursos que lo referencian; nunca es una entrada del catálogo."""
    __tablename__ = "fetcher_preset"
    __table_args__ = (
        UniqueConstraint("fetcher_id", "code", name="uq_fetcher_preset_code"),
        {"schema": "opendata"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    fetcher_id = Column(UUID(as_uuid=True), ForeignKey("opendata.fetcher.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    params = Column(JSONB, nullable=False, default=dict)
    # Candado selectivo (§6c): nombres de parámetros cuyo valor NO es pisable por el recurso.
    locked_params = Column(JSONB, nullable=False, default=list, server_default='[]')
    deleted_at = Column(DateTime, nullable=True)

    fetcher = relationship("Fetcher", back_populates="presets")
    resources = relationship("Resource", back_populates="preset")


class ResourceParam(AuditMixin, Base):
    """Parámetros key-value para cada Resource"""
    __tablename__ = "resource_param"
    __table_args__ = (
        {"schema": "opendata"}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    resource_id = Column(UUID(as_uuid=True), ForeignKey("opendata.resource.id", ondelete="CASCADE"), nullable=False)
    key = Column(String(100), nullable=False)
    value = Column(Text, nullable=False)
    is_external = Column(Boolean, default=False, nullable=False)

    resource = relationship("Resource", back_populates="params")


class ResourceCandidate(AuditMixin, Base):
    """Propuesta de agrupación inferida por el GroupingInferer a partir de las
    URLs hoja descubiertas por un crawler `Web Tree`. Promover una candidata crea
    un Resource hijo (auto_generated) cuyo fetcher en modo stream descarga las
    `matched_urls` y enriquece cada registro con las `dimensions` detectadas."""
    __tablename__ = "resource_candidate"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    execution_id = Column(UUID(as_uuid=True), ForeignKey("opendata.resource_execution.id", ondelete="SET NULL"), nullable=True)
    crawler_resource_id = Column(UUID(as_uuid=True), ForeignKey("opendata.resource.id", ondelete="CASCADE"), nullable=False)

    path_template = Column(Text, nullable=False)
    dimensions = Column(JSONB, nullable=False, default=list)
    matched_urls = Column(JSONB, nullable=False, default=list)
    file_types = Column(JSONB, nullable=False, default=dict)

    suggested_name = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)

    # Promoción heterogénea: un candidato puede declarar la ESPECIE del hijo y sus
    # params, en vez de heredar la del crawler padre. Imprescindible para nodrizas
    # de catálogo (el padre DESCUBRE, el hijo EXTRAE con otra especie). Si van NULL,
    # la promoción cae al comportamiento legacy (hereda fetcher del padre + root_url).
    target_fetcher_code = Column(String(50), nullable=True)
    target_params = Column(JSONB, nullable=True)

    status = Column(String(20), nullable=False, default="discovered")
    promoted_resource_id = Column(UUID(as_uuid=True), ForeignKey("opendata.resource.id", ondelete="SET NULL"), nullable=True)
    merged_into_id = Column(UUID(as_uuid=True), ForeignKey("opendata.resource_candidate.id", ondelete="SET NULL"), nullable=True)
    split_from_id = Column(UUID(as_uuid=True), ForeignKey("opendata.resource_candidate.id", ondelete="SET NULL"), nullable=True)

    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String(200), nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    crawler_resource = relationship("Resource", foreign_keys=[crawler_resource_id])
    promoted_resource = relationship("Resource", foreign_keys=[promoted_resource_id])
    execution = relationship("ResourceExecution")


class Subscriber(AuditMixin, Base):
    """Aplicaciones suscritas para recibir actualizaciones automáticas de core.models"""
    __tablename__ = "application"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    models_path = Column(String(255), nullable=True)  # Deprecated
    subscribed_projects = Column('subscribed_resources', JSONB, nullable=False, default=list)
    active = Column(Boolean, default=True)
    deleted_at = Column(DateTime, nullable=True)

    # Dataset system fields
    webhook_url = Column(String(500))
    webhook_secret = Column(String(100))
    consumption_mode = Column(String(20), nullable=False, default='webhook')
    persona_contacto = Column(String(160), nullable=True)
    email = Column(String(255), nullable=True)
    telefono = Column(String(40), nullable=True)
    github_url = Column(String(300), nullable=True)
    proposito = Column(Text, nullable=True)

    # Relationships
    subscriptions = relationship("ResourceSubscription", back_populates="application")


class FieldMetadata(AuditMixin, Base):
    """Metadatos de campos para tooltips y ayuda en UI"""
    __tablename__ = "field_metadata"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    table_name = Column(String(100), nullable=False)
    field_name = Column(String(100), nullable=False)
    label = Column(String(255))  # Etiqueta amigable para mostrar
    help_text = Column(Text)  # Texto de ayuda para tooltip
    placeholder = Column(String(255))  # Placeholder del input


class ResourceExecution(AuditMixin, Base):
    """Audit trail de ejecuciones de Resources"""
    __tablename__ = "resource_execution"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    resource_id = Column(UUID(as_uuid=True), ForeignKey("opendata.resource.id"), nullable=False)
    resource_name = Column(String(300), nullable=True)  # snapshot del nombre en el momento de ejecución

    # Runtime params that override/extend static ResourceParam values for this execution
    execution_params = Column(JSONB, nullable=True)

    # Execution tracking
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    status = Column(String(20))  # "running"|"completed"|"failed"|"aborted"|"paused"
    # Tipo de proceso: 'extraccion' (produce dataset) o 'discovering' (una
    # Colección rastreando su fuente para producir candidatos).
    kind = Column(String(20), nullable=False, default="extraccion", server_default="extraccion")

    # Cooperative pause signal — set True from outside to ask the streaming loop to stop
    # gracefully at the next page boundary and save state as "paused".
    pause_requested = Column(Boolean, default=False, nullable=False)

    # Accumulated active time in seconds (excludes paused periods).
    # Incremented each time the process pauses or completes.
    active_seconds = Column(Integer, nullable=True, default=0)

    # Results
    total_records = Column(Integer)
    records_loaded = Column(Integer)
    staging_path = Column(String(500))
    error_message = Column(Text)
    deleted_at = Column(DateTime, nullable=True)

    resource = relationship("Resource", back_populates="executions")


class RefrescoExtemporaneo(AuditMixin, Base):
    """Registro de refrescos a demanda (executeResource) para auditoría y cuota.

    Cada fila = un refresco extemporáneo solicitado por un usuario/aplicación.
    La cuota diaria se cuenta sobre estas filas (por usuario y día). Los refrescos
    PROGRAMADOS (scheduler) ejecutan FetcherManager directamente, no pasan por la
    mutation executeResource y por tanto NO consumen cuota ni se registran aquí.
    """
    __tablename__ = "refresco_extemporaneo"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    resource_id = Column(UUID(as_uuid=True), ForeignKey("opendata.resource.id", ondelete="CASCADE"), nullable=False, index=True)
    # El actor del refresco es `created_by_id` (AuditMixin); la cuota se cuenta por (created_by_id, created_at::date).

    resource = relationship("Resource")


class Dataset(AuditMixin, Base):
    """Versioned package de datos extraídos"""
    __tablename__ = "dataset"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    resource_id = Column(UUID(as_uuid=True), ForeignKey("opendata.resource.id"), nullable=False)
    execution_id = Column(UUID(as_uuid=True), ForeignKey("opendata.resource_execution.id"))

    # Versioning
    major_version = Column(Integer, nullable=False)
    minor_version = Column(Integer, nullable=False)
    patch_version = Column(Integer, nullable=False)

    # Human-readable label for this execution (e.g. "2023", "Q1-2024")
    label = Column(String(100), nullable=True)

    # Package contents
    schema_json = Column(JSONB, nullable=False)
    data_path = Column(String(500), nullable=False)
    record_count = Column(Integer)
    last_served_at = Column(DateTime, nullable=True)   # rastro de acceso (demanda)
    accesos = Column(Integer, default=0, nullable=False)
    checksum = Column(String(64))
    deleted_at = Column(DateTime, nullable=True)

    resource = relationship("Resource", back_populates="datasets")
    execution = relationship("ResourceExecution")

    @property
    def version_string(self) -> str:
        return f"{self.major_version}.{self.minor_version}.{self.patch_version}"


class ResourceSubscription(AuditMixin, Base):
    """Suscripciones pasivas de Subscribers a Resources"""
    __tablename__ = "resource_subscription"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("opendata.application.id"), nullable=False)
    resource_id = Column(UUID(as_uuid=True), ForeignKey("opendata.resource.id"), nullable=False)

    # Version pinning
    pinned_version = Column(String(20))  # "1.2.*" or "1.*" or "1.2.3"
    auto_upgrade = Column(String(20), default="patch")

    # State
    current_version = Column(String(20))
    notified_at = Column(DateTime)
    deleted_at = Column(DateTime, nullable=True)

    application = relationship("Subscriber", back_populates="subscriptions")
    resource = relationship("Resource")


class ResourceDependency(AuditMixin, Base):
    """Linaje entre recursos: el derivado depende del fuente con un rol
    ('left' | 'right' en CruceDatasets). Sincronizado automáticamente por el
    manager al ejecutar el derivado."""
    __tablename__ = "resource_dependency"
    __table_args__ = (
        UniqueConstraint("derived_resource_id", "source_resource_id", "role",
                         name="uq_resource_dependency"),
        {"schema": "opendata"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    derived_resource_id = Column(UUID(as_uuid=True), ForeignKey("opendata.resource.id", ondelete="CASCADE"), nullable=False)
    source_resource_id = Column(UUID(as_uuid=True), ForeignKey("opendata.resource.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(10), nullable=False)


class DerivedDatasetConfig(AuditMixin, Base):
    """Config for extracting derived/catalog datasets as a side-product of a resource execution.

    Example: while fetching BDNS concesiones, also extract beneficiarios (NIF + nombre)
    as a separate catalog, upserting by natural key (NIF).
    """
    __tablename__ = "derived_dataset_config"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    source_resource_id = Column(UUID(as_uuid=True), ForeignKey("opendata.resource.id", ondelete="CASCADE"), nullable=False)
    target_name = Column(String(100), nullable=False)     # e.g. "beneficiarios"
    key_field = Column(String(100), nullable=False)        # e.g. "nif", "codConvocatoria"
    extract_fields = Column(JSONB, nullable=False, default=list)  # ["nombre", "municipio", ...]
    merge_strategy = Column(String(20), default="upsert", nullable=False)  # "upsert" | "insert_only"
    enabled = Column(Boolean, default=True, nullable=False)
    description = Column(Text, nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    source_resource = relationship("Resource", back_populates="derived_configs")
    entries = relationship("DerivedDatasetEntry", back_populates="config", cascade="all, delete-orphan")


class DerivedDatasetEntry(AuditMixin, Base):
    """A single record in a derived dataset, stored as JSONB."""
    __tablename__ = "derived_dataset_entry"
    __table_args__ = (
        UniqueConstraint("config_id", "key_value", name="uq_derived_entry_config_key"),
        {"schema": "opendata"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    config_id = Column(UUID(as_uuid=True), ForeignKey("opendata.derived_dataset_config.id", ondelete="CASCADE"), nullable=False)
    key_value = Column(String(500), nullable=False)
    data = Column(JSONB, nullable=False)

    config = relationship("DerivedDatasetConfig", back_populates="entries")


class SubscriberNotification(AuditMixin, Base):
    """Log de webhooks enviados"""
    __tablename__ = "application_notification"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("opendata.application.id"), nullable=False)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("opendata.dataset.id"))

    sent_at = Column(DateTime, default=datetime.utcnow)
    status_code = Column(Integer)
    response_body = Column(Text)
    error_message = Column(Text)

    application = relationship("Subscriber")
    dataset = relationship("Dataset")


# ─────────────────────────────────────────────────────────────────────────
# RBAC: usuarios, roles, funcionalidades (catálogo de transacciones) y sesiones
# ─────────────────────────────────────────────────────────────────────────
from sqlalchemy import Table  # noqa: E402

usuario_rol = Table(
    "usuario_rol", Base.metadata,
    Column("usuario_id", UUID(as_uuid=True), ForeignKey("opendata.usuario.id", ondelete="CASCADE"), primary_key=True),
    Column("rol_id", UUID(as_uuid=True), ForeignKey("opendata.rol.id", ondelete="CASCADE"), primary_key=True),
    schema="opendata",
)

rol_funcionalidad = Table(
    "rol_funcionalidad", Base.metadata,
    Column("rol_id", UUID(as_uuid=True), ForeignKey("opendata.rol.id", ondelete="CASCADE"), primary_key=True),
    Column("funcionalidad_id", UUID(as_uuid=True), ForeignKey("opendata.funcionalidad.id", ondelete="CASCADE"), primary_key=True),
    schema="opendata",
)


class Usuario(AuditMixin, Base):
    __tablename__ = "usuario"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    # Discriminador de principal (§12): 'humano' inicia sesión por cookie;
    # 'aplicacion' es una cuenta de servicio M2M que se autentica por token
    # Bearer (ver ServiceToken). Reutiliza el plumbing de RBAC/auditoría/cuota.
    tipo = Column(String(20), nullable=False, default="humano", server_default="humano")
    notificar_email = Column(Boolean, default=False, nullable=False)  # avisos de novedades
    last_login_at = Column(DateTime, nullable=True)
    cuota_refrescos_diaria = Column(Integer, default=50, nullable=False)  # refrescos a demanda/día (executeResource); 0 = sin refrescos extemporáneos

    roles = relationship("Rol", secondary=usuario_rol, back_populates="usuarios")


class Rol(AuditMixin, Base):
    __tablename__ = "rol"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    code = Column(String(50), unique=True, nullable=False)
    nombre = Column(String(120), nullable=False)
    descripcion = Column(Text, nullable=True)
    is_system = Column(Boolean, default=False, nullable=False)  # roles base no borrables

    usuarios = relationship("Usuario", secondary=usuario_rol, back_populates="roles")
    funcionalidades = relationship("Funcionalidad", secondary=rol_funcionalidad, back_populates="roles")


class Funcionalidad(AuditMixin, Base):
    """Catálogo de transacciones/permisos (p. ej. 'recursos.crear')."""
    __tablename__ = "funcionalidad"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    code = Column(String(80), unique=True, nullable=False)
    nombre = Column(String(160), nullable=False)
    descripcion = Column(Text, nullable=True)
    modulo = Column(String(80), nullable=True)
    es_lectura = Column(Boolean, default=False, nullable=False)  # accesible a invitado si True

    roles = relationship("Rol", secondary=rol_funcionalidad, back_populates="funcionalidades")


class Sesion(AuditMixin, Base):
    """Sesión opaca en BD (cookie httpOnly). Revocable borrando la fila."""
    __tablename__ = "sesion"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("opendata.usuario.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)  # sha256 del token
    expires_at = Column(DateTime, nullable=False)
    last_seen_at = Column(DateTime, nullable=True)

    usuario = relationship("Usuario", foreign_keys=[usuario_id])


class SolicitudIngreso(AuditMixin, Base):
    """§12 — Solicitud self-service de una aplicación para ingresar en ODM.

    No crea nada operativo por sí sola. El admin la revisa y, al aprobarla, se
    materializa el principal 'aplicacion' (un Usuario tipo='aplicacion') y se
    vincula aquí en ``usuario_id`` para trazabilidad.
    """
    __tablename__ = "solicitud_ingreso"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    nombre = Column(String(120), nullable=False)          # nombre de la aplicación
    contacto = Column(String(255), nullable=True)         # email/responsable
    proposito = Column(Text, nullable=True)               # para qué quiere los datos
    descripcion = Column(Text, nullable=True)             # qué hace la aplicación
    persona_contacto = Column(String(160), nullable=True) # responsable
    email = Column(String(255), nullable=True)            # email de contacto
    telefono = Column(String(40), nullable=True)
    github_url = Column(String(300), nullable=True)       # repo de la aplicación
    consumption_mode = Column(String(20), nullable=True)  # webhook|graphql|both
    ambito_solicitado = Column(JSONB, nullable=True)      # scopes/recursos pedidos
    estado = Column(String(20), nullable=False, default="pendiente", server_default="pendiente")  # pendiente|aprobada|rechazada
    motivo = Column(Text, nullable=True)                  # motivo de rechazo / nota de aprobación
    resuelta_at = Column(DateTime, nullable=True)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("opendata.usuario.id", ondelete="SET NULL"), nullable=True)
    # §12 push: callback al que ODM empuja la resolución (la app aún no tiene
    # webhook propio cuando solicita). El secreto lo aporta el solicitante.
    callback_url = Column(String(500), nullable=True)
    callback_secret = Column(String(200), nullable=True)

    usuario = relationship("Usuario", foreign_keys=[usuario_id])


class ServiceToken(AuditMixin, Base):
    """§12 — Credencial Bearer de una aplicación (cuenta de servicio).

    Nombrado ServiceToken (no 'ApplicationToken') a propósito: el principal es
    un Usuario tipo='aplicacion', y ya existe una clase ``Subscriber`` con otro
    significado (suscripción a webhooks de datasets). El token cuelga del
    usuario funcional. En reposo solo vive el HASH (sha256); el secreto en claro
    se muestra una sola vez al emitirlo. Varios tokens por app → rotación sin
    corte. ``prefix`` (visible, no secreto) permite localizar el candidato sin
    desvelar nada y habilita el escaneo de secretos por 'odm_app_'.
    """
    __tablename__ = "service_token"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("opendata.usuario.id", ondelete="CASCADE"), nullable=False)
    label = Column(String(120), nullable=True)            # etiqueta humana ('CI', 'prod', ...)
    prefix = Column(String(24), nullable=False, index=True)  # 'odm_app_' + primeros chars (localización)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)  # sha256 del secreto completo
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)          # TTL opcional (None = sin caducidad)
    revoked_at = Column(DateTime, nullable=True)          # revocación inmediata

    usuario = relationship("Usuario", foreign_keys=[usuario_id])


class ResourceManifestVersion(AuditMixin, Base):
    """Historial de versiones del manifiesto canónico de un recurso.

    Cada cambio (por UI o por importación de manifiesto) escribe una fila, lo
    que da auditoría, trazabilidad de origen y rollback.
    """
    __tablename__ = "resource_manifest_version"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    resource_id = Column(UUID(as_uuid=True), ForeignKey("opendata.resource.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False)
    manifest_json = Column(JSONB, nullable=False)   # manifiesto canónico de ESE recurso
    hash = Column(String(64), nullable=False)
    origin = Column(String(20), nullable=False)     # ui | manifest | seed
    author = Column(String(120), nullable=True)     # username, o 'manifest:<fichero>'


class Evento(AuditMixin, Base):
    """Novedad del sistema susceptible de aviso (alta/baja de recurso, conflicto…).
    Se genera al importar manifiestos o detectar cambios de origen; el despacho
    de emails marca `notificado`."""
    __tablename__ = "evento"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tipo = Column(String(40), nullable=False)        # recurso.alta | recurso.baja | recurso.conflicto | ejecucion.fallo
    recurso_id = Column(UUID(as_uuid=True), ForeignKey("opendata.resource.id", ondelete="SET NULL"), nullable=True)
    titulo = Column(String(300), nullable=False)
    detalle = Column(JSONB, nullable=True)
    notificado = Column(Boolean, default=False, nullable=False)
