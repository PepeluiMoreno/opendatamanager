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
    sources = relationship("Source", back_populates="fetcher_type")


class TypeFetcherParams(Base):
    __tablename__ = "type_fetcher_params"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    fetcher_type_id = Column(UUID(as_uuid=True), ForeignKey("opendata.fetcher_type.id"))
    param_name = Column(String(100), nullable=False)
    required = Column(Boolean, default=True)
    data_type = Column(String(20), default="string")

    fetcher_type = relationship("FetcherType", back_populates="params_def")


class Source(Base):
    __tablename__ = "source"
    __table_args__ = {"schema": "opendata"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), unique=True, nullable=False)
    project = Column(String(50), nullable=False)
    fetcher_type_id = Column(UUID(as_uuid=True), ForeignKey("opendata.fetcher_type.id"))
    params = Column(JSONB, nullable=False)
    active = Column(Boolean, default=True)

    fetcher_type = relationship("FetcherType", back_populates="sources")
