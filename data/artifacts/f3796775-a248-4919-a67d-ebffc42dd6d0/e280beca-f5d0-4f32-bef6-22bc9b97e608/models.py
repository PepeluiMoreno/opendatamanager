"""
Auto-generated models for: INE - Población por Municipios
Generated: 2026-01-10T22:56:15.948601
Version: Auto-generated from dataset
DO NOT EDIT MANUALLY - Download new version from OpenDataManager
"""
from uuid import uuid4
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class InePopulation(Base):
    """
    Dataset: INE - Población por Municipios
    Publisher: Instituto Nacional de Estadística
    """
    __tablename__ = "ine_population"
    __table_args__ = {"schema": "core"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    COD = Column(String(255), nullable=False)
    Nombre = Column(String(255), nullable=False)
    FK_Unidad = Column(Integer, nullable=False)
    FK_Escala = Column(Integer, nullable=False)
    Data = Column(JSONB, nullable=False)
