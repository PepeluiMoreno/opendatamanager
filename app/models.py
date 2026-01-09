from uuid import uuid4
from sqlalchemy import Column, String, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base

class FetcherType(Base):
    __tablename__ = "fetcher_type"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    code = Column(String(50), unique=True, nullable=False)
    class_path = Column(String(255), nullable=False)
    description = Column(Text)

    params_def = relationship("TypeFetcherParams", back_populates="fetcher_type")
    resources = relationship("Resource", back_populates="fetcher_type")


class TypeFetcherParams(Base):
    __tablename__ = "type_fetcher_params"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    fetcher_type_id = Column(UUID(as_uuid=True), ForeignKey("opendata.fetcher_type.id"))
    param_name = Column(String(100), nullable=False)
    required = Column(Boolean, default=True)
    data_type = Column(String(20), default="string")

    fetcher_type = relationship("FetcherType", back_populates="params_def")


class Resource(Base):
    __tablename__ = "resource"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    publisher = Column(String(50), nullable=False)
    target_table = Column(String(100), nullable=False)
    fetcher_type_id = Column(UUID(as_uuid=True), ForeignKey("opendata.fetcher_type.id"))
    active = Column(Boolean, default=True)

    fetcher_type = relationship("FetcherType", back_populates="resources")
    params = relationship("ResourceParam", back_populates="resource", cascade="all, delete-orphan")


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
    subscribed_projects = Column(JSONB, nullable=False, default=list)  # Lista de projects a los que está suscrita
    active = Column(Boolean, default=True)


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
