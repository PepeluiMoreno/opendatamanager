"""
Generador de modelos SQLAlchemy para aplicaciones externas.
Lee datos desde la API GraphQL y genera archivos Python con modelos.
"""
from typing import List, Dict, Any
from pathlib import Path
import json


class ModelGenerator:
    """Genera archivos de modelos SQLAlchemy desde datos de la API GraphQL"""

    def __init__(self, api_url: str):
        self.api_url = api_url

    def generate_models_for_application(
        self,
        app_name: str,
        subscribed_projects: List[str],
        models_path: str
    ) -> None:
        """
        Genera modelos SQLAlchemy para una aplicación.

        Args:
            app_name: Nombre de la aplicación
            subscribed_projects: Lista de projects a los que está suscrita
            models_path: Ruta donde escribir los archivos generados
        """
        print(f"📦 Generando modelos para aplicación '{app_name}'...")

        for project in subscribed_projects:
            self._generate_project_models(project, models_path)

        print(f"✅ Modelos generados en: {models_path}")

    def _generate_project_models(self, project: str, output_path: str) -> None:
        """
        Genera el archivo de modelos para un proyecto específico.

        Args:
            project: Nombre del proyecto
            output_path: Directorio donde escribir el archivo
        """
        # TODO: Consultar API GraphQL para obtener schema del proyecto
        # Por ahora, generar un modelo de ejemplo

        output_file = Path(output_path) / f"{project}_models.py"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        model_code = self._build_model_code(project)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(model_code)

        print(f"  ✓ Generado: {output_file}")

    def _build_model_code(self, project: str) -> str:
        """
        Construye el código Python del modelo.

        Args:
            project: Nombre del proyecto

        Returns:
            Código Python como string
        """
        # Template básico
        return f'''"""
Modelos auto-generados para el proyecto: {project}
Generado automáticamente por OpenDataManager.
NO EDITAR MANUALMENTE - será sobrescrito en cada refresh.
"""
from uuid import uuid4
from sqlalchemy import Column, String, Boolean, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class {project.capitalize()}Data(Base):
    """Datos del proyecto {project}"""
    __tablename__ = "{project}_data"
    __table_args__ = {{"schema": "opendata"}}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    data = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    active = Column(Boolean, default=True)

    def __repr__(self):
        return f"<{project.capitalize()}Data(id={{self.id}})>"
'''
