"""
Auto-generated models for: Registro de entidades religiosas católicas
Generated: 2026-01-09T18:38:23.046944
Version: Auto-generated from artifact
DO NOT EDIT MANUALLY - Download new version from OpenDataManager
"""
from uuid import uuid4
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class MinisterioJusticia(Base):
    """
    Dataset: Registro de entidades religiosas católicas
    Publisher: Ministerio de Justicia
    """
    __tablename__ = "ministerio_justicia"
    __table_args__ = {"schema": "core"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    source_type = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    raw_html_length = Column(Integer, nullable=False)
    tables_count = Column(Integer, nullable=False)
    forms_count = Column(Integer, nullable=False)
    parsed_data = Column(JSONB, nullable=False)
