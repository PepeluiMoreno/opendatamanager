"""
Auto-generated models for: BDNS - Convocatorias de Subvenciones
Generated: 2026-01-12T00:50:16.002541
Version: Auto-generated from dataset
DO NOT EDIT MANUALLY - Download new version from OpenDataManager
"""
from uuid import uuid4
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class BdnsGrants(Base):
    """
    Dataset: BDNS - Convocatorias de Subvenciones
    Publisher: IGAE
    """
    __tablename__ = "bdns_grants"
    __table_args__ = {"schema": "core"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    content = Column(JSONB, nullable=False)
    pageable = Column(JSONB, nullable=False)
    last = Column(Boolean, nullable=False)
    totalElements = Column(Integer, nullable=False)
    totalPages = Column(Integer, nullable=False)
    first = Column(Boolean, nullable=False)
    sort = Column(JSONB, nullable=False)
    numberOfElements = Column(Integer, nullable=False)
    size = Column(Integer, nullable=False)
    number = Column(Integer, nullable=False)
    empty = Column(Boolean, nullable=False)
    advertencia = Column(String(255), nullable=False)
