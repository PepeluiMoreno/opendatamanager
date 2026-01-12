"""
Manager para ejecutar fetchers y actualizar datos en BD.
"""
import os
import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import Resource, ResourceExecution, Artifact
from app.fetchers.factory import FetcherFactory
from app.builders.artifact_builder import ArtifactBuilder
from app.services.notification_service import NotificationService
from app.core import upsert


class FetcherManager:
    """Orquestador de ejecución de fetchers"""

    @staticmethod
    def _make_serializable(obj):
        """Convert non-serializable objects to JSON-serializable format"""
        from bs4 import BeautifulSoup, Tag
        from bs4.element import NavigableString

        if isinstance(obj, dict):
            return {k: FetcherManager._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [FetcherManager._make_serializable(item) for item in obj]
        elif isinstance(obj, (BeautifulSoup, Tag)):
            # Convert BeautifulSoup/Tag to string
            return str(obj)
        elif isinstance(obj, NavigableString):
            return str(obj)
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        else:
            # For any other type, convert to string
            return str(obj)

    @staticmethod
    def run(session: Session, resource_id: str) -> Artifact:
        """
        Ejecuta pipeline: EXTRACT → STAGE → ARTIFACT

        Args:
            session: Sesión SQLAlchemy activa
            resource_id: UUID del Resource a ejecutar

        Returns:
            Artifact record with versioned package
        """
        # Load resource
        resource = session.query(Resource).filter(Resource.id == resource_id).first()

        if not resource:
            raise ValueError(f"Resource con id '{resource_id}' no encontrado")

        if not resource.active:
            print(f"Resource '{resource.name}' está desactivado, omitiendo...")
            return None

        print(f"Ejecutando Resource: {resource.name} (publisher: {resource.publisher})")

        # Create execution record
        execution = ResourceExecution(
            resource_id=resource_id,
            status="running",
            started_at=datetime.utcnow()
        )
        session.add(execution)
        session.flush()  # Get execution.id

        try:
            # 1. EXTRACT
            print(f"  [1/3] EXTRACT - Fetching data...")
            fetcher = FetcherFactory.create_from_resource(resource)
            data = fetcher.execute()

            # 2. STAGE - Write to filesystem
            print(f"  [2/3] STAGE - Writing to staging...")
            staging_dir = f"data/staging/{resource_id}"
            os.makedirs(staging_dir, exist_ok=True)

            # Normalize data to list format
            if isinstance(data, dict):
                data_list = [data]
            elif isinstance(data, list):
                data_list = data
            else:
                raise ValueError(f"Unexpected data type from fetcher: {type(data)}")

            staging_path = f"{staging_dir}/{execution.id}.jsonl"
            with open(staging_path, 'w', encoding='utf-8') as f:
                for item in data_list:
                    # Convert to JSON-serializable format
                    serializable_item = FetcherManager._make_serializable(item)
                    f.write(json.dumps(serializable_item, ensure_ascii=False) + '\n')

            # Update execution
            execution.staging_path = staging_path
            execution.total_records = len(data_list)

            # 3. ARTIFACT - Generate package
            artifact_builder = ArtifactBuilder()
            artifact = artifact_builder.build(
                session=session,
                resource=resource,
                execution=execution,
                data=data_list
            )
            session.add(artifact)

            # 4. LOAD (optional) - Upsert to core schema
            if resource.enable_load:
                print(f"  [4/5] LOAD - Loading data to core.{resource.target_table}...")
                try:
                    upsert(
                        session=session,
                        target_model=resource.target_table,
                        data=data_list,
                        mode=resource.load_mode or "replace"
                    )
                    execution.records_loaded = len(data_list)
                    print(f"    Loaded {execution.records_loaded} records")
                except Exception as e:
                    execution.error_message = f"Load failed: {str(e)}"
                    print(f"    Load failed: {e}")
                    # Don't fail the whole pipeline if load fails

            # 5. NOTIFY - Send webhooks
            notification_service = NotificationService()
            notification_service.notify_subscribers(session, artifact)

            # Update execution
            execution.status = "completed"
            execution.completed_at = datetime.utcnow()

            print(f"Resource '{resource.name}' completado - Artifact v{artifact.version_string}")

        except Exception as e:
            execution.status = "failed"
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            print(f"Error en Resource '{resource.name}': {e}")
            raise

        finally:
            session.commit()

        return artifact

    @staticmethod
    def run_all(session: Session) -> None:
        """
        Ejecuta todos los Resources activos.

        Args:
            session: Sesión SQLAlchemy activa
        """
        resources = session.query(Resource).filter(Resource.active == True).all()

        if not resources:
            print("No hay resources activos para ejecutar")
            return

        print(f"Ejecutando {len(resources)} resources activos...")

        for resource in resources:
            try:
                FetcherManager.run(session, str(resource.id))
            except Exception as e:
                print(f"Error en Resource '{resource.name}': {e}")
                continue

        print("Ejecucion completada")

    @staticmethod
    def fetch_only(session: Session, resource_id: str, limit: int = 10) -> list:
        """
        Extract data only (no staging, no artifact, no load)
        
        Args:
            session: Sesión SQLAlchemy activa
            resource_id: UUID del Resource a ejecutar
            limit: Maximum number of records to return
            
        Returns:
            List of extracted data records
        """
        # Load resource
        resource = session.query(Resource).filter(Resource.id == resource_id).first()

        if not resource:
            raise ValueError(f"Resource con id '{resource_id}' no encontrado")

        if not resource.active:
            print(f"Resource '{resource.name}' está desactivado, omitiendo...")
            return []

        print(f"Extracting data from: {resource.name} (limit: {limit})")

        # Extract data only
        fetcher = FetcherFactory.create_from_resource(resource)
        data = fetcher.execute()

        # Normalize data to list format
        if isinstance(data, dict):
            data_list = [data]
        elif isinstance(data, list):
            data_list = data
        else:
            raise ValueError(f"Unexpected data type from fetcher: {type(data)}")

        # Make serializable and apply limit
        serializable_data = [FetcherManager._make_serializable(item) for item in data_list]
        limited_data = serializable_data[:limit]
        
        print(f"  Extracted {len(limited_data)} records (limited from {len(data_list)})")
        return limited_data