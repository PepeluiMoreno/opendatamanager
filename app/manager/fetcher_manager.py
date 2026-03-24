"""
Manager para ejecutar fetchers y actualizar datos en BD.
"""
import os
import json
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.models import Resource, ResourceExecution, Dataset
from app.fetchers.factory import FetcherFactory
from app.builders.dataset_builder import DatasetBuilder
from app.services.notification_service import NotificationService
from app.services.data_loader_service import DataLoaderService, stage_data


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
    def run(session: Session, resource_id: str, execution_params: Optional[dict] = None) -> Optional[Dataset]:
        """
        Ejecuta pipeline: EXTRACT → STAGE (→ DATASET - TODO)

        Args:
            session: Sesión SQLAlchemy activa
            resource_id: UUID del Resource a ejecutar
            execution_params: Parámetros runtime que sobreescriben/amplían los ResourceParam estáticos

        Returns:
            None (Dataset creation pending implementation)
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
            started_at=datetime.utcnow(),
            execution_params=execution_params,
        )
        session.add(execution)
        session.flush()  # Get execution.id

        try:
            # 1. EXTRACT
            print(f"  [1/3] EXTRACT - Fetching data...")
            fetcher = FetcherFactory.create_from_resource(resource, execution_params)
            data = fetcher.execute()

            # 2. STAGE - Write to filesystem
            print(f"  [2/5] STAGE - Writing to staging...")
            # Normalize data to list format
            if isinstance(data, dict):
                data_list = [data]
            elif isinstance(data, list):
                data_list = data
            else:
                raise ValueError(f"Unexpected data type from fetcher: {type(data)}")

            staging_dir = f"data/staging/{resource_id}"
            staging_path = stage_data(data_list, staging_dir, str(execution.id))

            # Update execution
            execution.staging_path = staging_path
            execution.total_records = len(data_list)

            # 3. DATASET - Generate package
            print(f"  [3/5] DATASET - Building dataset...")
            dataset_builder = DatasetBuilder()
            dataset = dataset_builder.build(
                session=session,
                resource=resource,
                execution=execution,
                data=data_list
            )
            session.add(dataset)

            # 4. LOAD (optional) - Upsert to core schema
            if resource.enable_load:
                print(f"  [4/5] LOAD - Loading data to core.{resource.target_table}...")
                data_loader = DataLoaderService()
                try:
                    loaded_count = data_loader.load_data(
                        session=session,
                        dataset=dataset,
                        normalized_data=data_list,
                        load_mode=resource.load_mode or "upsert"
                    )
                    execution.records_loaded = loaded_count
                except Exception as e:
                    execution.error_message = f"Load failed: {str(e)}"
                    print(f"    Load failed: {e}")
                    # Don't fail the whole pipeline if load fails

            # 5. NOTIFY - Send webhooks
            print(f"  [5/5] NOTIFY - Sending notifications...")
            notification_service = NotificationService()
            notification_service.notify_subscribers(session, dataset)

            # Update execution
            execution.status = "completed"
            execution.completed_at = datetime.utcnow()

            print(f"Resource '{resource.name}' completado - {len(data_list)} records")

        except Exception as e:
            execution.status = "failed"
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            print(f"Error en Resource '{resource.name}': {e}")
            raise

        finally:
            session.commit()

        return dataset

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
        Extract data only (no staging, no dataset, no load)
        
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
        # Hint al fetcher para que corte temprano en modo preview
        fetcher.params["_preview_limit"] = limit
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