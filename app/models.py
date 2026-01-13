from uuid import uuid4
from datetime import datetime
from sqlalchemy import Column, String, Boolean, ForeignKey, Text, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base

class FetcherType(Base):
    __tablename__ = "fetcher"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    # DB migrations renamed this column to 'name' — keep attribute `code`
    # mapped to DB column 'name' for backward compatibility in code.
    code = Column('name', String(50), unique=True, nullable=False)
    class_path = Column(String(255), nullable=True)  # Python class path for dynamic import
    description = Column(Text)

    params_def = relationship("TypeFetcherParams", back_populates="fetcher")
    resources = relationship("Resource", back_populates="fetcher")


class TypeFetcherParams(Base):
    __tablename__ = "type_fetcher_params"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    fetcher_id = Column(UUID(as_uuid=True), ForeignKey("opendata.fetcher.id"))
    param_name = Column(String(100), nullable=False)
    required = Column(Boolean, default=True)
    data_type = Column(String(20), default="string")
    default_value = Column(JSONB, nullable=True)
    enum_values = Column(JSONB, nullable=True)  # For enum type: list of allowed values

    fetcher = relationship("FetcherType", back_populates="params_def")


class Resource(Base):
    __tablename__ = "resource"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    publisher = Column(String(50), nullable=False)
    target_table = Column(String(100), nullable=False)
    fetcher_id = Column(UUID(as_uuid=True), ForeignKey("opendata.fetcher.id"))
    active = Column(Boolean, default=True)

    # New fields for artifact system
    enable_load = Column(Boolean, default=False)
    load_mode = Column(String(20), default="replace")

    fetcher = relationship("FetcherType", back_populates="resources")
    params = relationship("ResourceParam", back_populates="resource", cascade="all, delete-orphan")
    executions = relationship("ResourceExecution", back_populates="resource")
    artifacts = relationship("Artifact", back_populates="resource")


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

    resource = relationship("Resource", back_populates="params")


class Application(Base):
    """Aplicaciones suscritas para recibir actualizaciones automáticas de core.models"""
    __tablename__ = "application"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    models_path = Column(String(255), nullable=False)  # Ruta donde escribir los modelos generados
    subscribed_projects = Column('subscribed_resources', JSONB, nullable=False, default=list)  # Lista de resources a los que está suscrita
    active = Column(Boolean, default=True)

    # New fields for artifact system
    webhook_url = Column(String(500))
    webhook_secret = Column(String(100))

    # New relationships
    subscriptions = relationship("ArtifactSubscription", back_populates="application")


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

    # Execution tracking
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    status = Column(String(20))  # "running"|"completed"|"failed"

    # Results
    total_records = Column(Integer)
    records_loaded = Column(Integer)
    staging_path = Column(String(500))
    error_message = Column(Text)

    resource = relationship("Resource", back_populates="executions")


class Artifact(Base):
    """Versioned package de datos extraídos"""
    __tablename__ = "artifact"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    resource_id = Column(UUID(as_uuid=True), ForeignKey("opendata.resource.id"), nullable=False)
    execution_id = Column(UUID(as_uuid=True), ForeignKey("opendata.resource_execution.id"))

    # Versioning
    major_version = Column(Integer, nullable=False)
    minor_version = Column(Integer, nullable=False)
    patch_version = Column(Integer, nullable=False)

    # Package contents
    schema_json = Column(JSONB, nullable=False)
    data_path = Column(String(500), nullable=False)
    record_count = Column(Integer)
    checksum = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)

    resource = relationship("Resource", back_populates="artifacts")
    execution = relationship("ResourceExecution")

    @property
    def version_string(self) -> str:
        return f"{self.major_version}.{self.minor_version}.{self.patch_version}"


class ArtifactSubscription(Base):
    """Suscripciones pasivas de Applications a Resources"""
    __tablename__ = "artifact_subscription"
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

    application = relationship("Application", back_populates="subscriptions")
    resource = relationship("Resource")


class ApplicationNotification(Base):
    """Log de webhooks enviados"""
    __tablename__ = "application_notification"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("opendata.application.id"), nullable=False)
    artifact_id = Column(UUID(as_uuid=True), ForeignKey("opendata.artifact.id"))

    sent_at = Column(DateTime, default=datetime.utcnow)
    status_code = Column(Integer)
    response_body = Column(Text)
    error_message = Column(Text)

    application = relationship("Application")
    artifact = relationship("Artifact")
