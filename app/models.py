from uuid import uuid4
from datetime import datetime
from sqlalchemy import Column, String, Boolean, ForeignKey, Text, Integer, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class AppConfig(Base):
    """Global application settings stored as key-value pairs."""
    __tablename__ = "app_config"
    __table_args__ = {"schema": "opendata"}

    key = Column(String(100), primary_key=True)
    value = Column(JSONB, nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Fetcher(Base):
    __tablename__ = "fetcher"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    # DB migrations renamed this column to 'name' — keep attribute `code`
    # mapped to DB column 'name' for backward compatibility in code.
    code = Column('name', String(50), unique=True, nullable=False)
    class_path = Column(String(255), nullable=True)
    description = Column(Text)
    deleted_at = Column(DateTime, nullable=True)

    params_def = relationship("FetcherParams", back_populates="fetcher")
    resources = relationship("Resource", back_populates="fetcher")


class FetcherParams(Base):
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

    fetcher = relationship("Fetcher", back_populates="params_def")


class Publisher(Base):
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
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    resources = relationship("Resource", back_populates="publisher_obj")


class Resource(Base):
    __tablename__ = "resource"
    __table_args__ = {"schema": "opendata"}

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

    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    fetcher = relationship("Fetcher", back_populates="resources")
    publisher_obj = relationship("Publisher", back_populates="resources")
    params = relationship("ResourceParam", back_populates="resource", cascade="all, delete-orphan")
    executions = relationship("ResourceExecution", back_populates="resource")
    datasets = relationship("Dataset", back_populates="resource")
    derived_configs = relationship("DerivedDatasetConfig", back_populates="source_resource", cascade="all, delete-orphan")


class ResourceParam(Base):
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


class Application(Base):
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

    # Relationships
    subscriptions = relationship("DatasetSubscription", back_populates="application")


class FieldMetadata(Base):
    """Metadatos de campos para tooltips y ayuda en UI"""
    __tablename__ = "field_metadata"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    table_name = Column(String(100), nullable=False)
    field_name = Column(String(100), nullable=False)
    label = Column(String(255))  # Etiqueta amigable para mostrar
    help_text = Column(Text)  # Texto de ayuda para tooltip
    placeholder = Column(String(255))  # Placeholder del input


class ResourceExecution(Base):
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


class Dataset(Base):
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
    checksum = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)

    resource = relationship("Resource", back_populates="datasets")
    execution = relationship("ResourceExecution")

    @property
    def version_string(self) -> str:
        return f"{self.major_version}.{self.minor_version}.{self.patch_version}"


class DatasetSubscription(Base):
    """Suscripciones pasivas de Applications a Resources"""
    __tablename__ = "dataset_subscription"
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

    application = relationship("Application", back_populates="subscriptions")
    resource = relationship("Resource")


class DerivedDatasetConfig(Base):
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
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    source_resource = relationship("Resource", back_populates="derived_configs")
    entries = relationship("DerivedDatasetEntry", back_populates="config", cascade="all, delete-orphan")


class DerivedDatasetEntry(Base):
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
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    config = relationship("DerivedDatasetConfig", back_populates="entries")


class ApplicationNotification(Base):
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

    application = relationship("Application")
    dataset = relationship("Dataset")
