"""
Manager para ejecutar fetchers y actualizar datos en BD.
"""
import os
import json
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.models import Resource, ResourceExecution, Dataset, DerivedDatasetConfig, DerivedDatasetEntry
from app.fetchers.factory import FetcherFactory
from app.builders.dataset_builder import DatasetBuilder
from app.services.notification_service import NotificationService
from app.services.data_loader_service import DataLoaderService

LOG_DIR = "data/logs"


class ExecutionLogger:
    """Writes timestamped log lines to a per-execution file and stdout.
    Also captures Python logging records from the 'app.fetchers' hierarchy."""

    def __init__(self, execution_id: str):
        os.makedirs(LOG_DIR, exist_ok=True)
        self.log_path = f"{LOG_DIR}/{execution_id}.log"
        self._file = open(self.log_path, "a", buffering=1)
        # Attach a logging handler so fetcher logger.info/warning calls land here
        self._handler = logging.StreamHandler(self._file)
        self._handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"))
        self._handler.setLevel(logging.DEBUG)
        self._root_logger = logging.getLogger("app.fetchers")
        self._prev_level = self._root_logger.level
        self._root_logger.addHandler(self._handler)
        self._root_logger.setLevel(logging.DEBUG)

    def log(self, message: str):
        ts = datetime.utcnow().strftime("%H:%M:%S")
        line = f"[{ts}] {message}"
        print(line)
        self._file.write(line + "\n")
        self._file.flush()

    def close(self):
        self._root_logger.removeHandler(self._handler)
        self._root_logger.setLevel(self._prev_level)
        self._handler.close()
        self._file.close()


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
    def run(session: Session, resource_id: str, execution_params: Optional[dict] = None, execution_id: Optional[str] = None) -> Optional[Dataset]:
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

        # Use pre-created execution record if provided, otherwise create one now
        if execution_id:
            execution = session.query(ResourceExecution).filter(
                ResourceExecution.id == execution_id
            ).first()
            if not execution:
                raise ValueError(f"Execution '{execution_id}' not found")
        else:
            execution = ResourceExecution(
                resource_id=resource_id,
                status="running",
                started_at=datetime.utcnow(),
                execution_params=execution_params,
            )
            session.add(execution)
            session.commit()  # Commit immediately so execution is visible as "running"

        logger = ExecutionLogger(str(execution.id))
        try:
            logger.log(f"Ejecutando Resource: {resource.name} (publisher: {resource.publisher})")

            # 1. EXTRACT + STAGE (streaming — one page written to disk at a time)
            logger.log("[1/5] EXTRACT+STAGE - Streaming data to staging file...")
            fetcher = FetcherFactory.create_from_resource(resource, execution_params)

            staging_dir = f"data/staging/{resource_id}"
            os.makedirs(staging_dir, exist_ok=True)
            staging_path = os.path.join(staging_dir, f"{execution.id}.jsonl")

            total_records = 0
            paused = False
            # Campos internos que no se persisten en el staging
            _STAGING_EXCLUDE = {"raw_xml_content", "raw_html", "_raw"}

            with open(staging_path, "w", encoding="utf-8") as f:
                for chunk in fetcher.stream():
                    for record in chunk:
                        clean = {k: v for k, v in record.items() if k not in _STAGING_EXCLUDE}
                        serializable = FetcherManager._make_serializable(clean)
                        f.write(json.dumps(serializable, ensure_ascii=False) + "\n")
                    total_records += len(chunk)
                    execution.total_records = total_records
                    session.commit()  # Progressive persistence — survives a restart
                    logger.log(f"  Staged {total_records} records so far...")

                    # Check cooperative pause signal (set by exclusive mode or manual pause)
                    session.refresh(execution)
                    if execution.pause_requested:
                        paused = True
                        logger.log(f"  Pause requested — stopping at {total_records} records")
                        break

            if paused:
                execution.status = "paused"
                execution.completed_at = datetime.utcnow()
                logger.log(f"PAUSED — {total_records} records staged. Resume to restart.")
                session.commit()
                logger.close()
                return None

            execution.staging_path = staging_path
            session.commit()
            logger.log(f"  Done: {total_records} records → {staging_path}")

            # 2. DATASET - Generate package
            logger.log("[2/5] DATASET - Building dataset...")
            dataset_builder = DatasetBuilder()
            dataset = dataset_builder.build(
                session=session,
                resource=resource,
                execution=execution,
            )
            session.add(dataset)
            logger.log(f"  Dataset created: {dataset.version_string}")

            # 3. DERIVE - Extract side-product catalog datasets
            derived_configs = session.query(DerivedDatasetConfig).filter(
                DerivedDatasetConfig.source_resource_id == resource_id,
                DerivedDatasetConfig.enabled == True,
            ).all()
            if derived_configs:
                logger.log(f"[3/5] DERIVE - Processing {len(derived_configs)} derived dataset(s)...")
                for cfg in derived_configs:
                    FetcherManager._derive_dataset(session, cfg, staging_path, logger)
            else:
                logger.log("[3/5] DERIVE - Skipped (no configs enabled)")

            # 4. LOAD (optional) - Upsert to core schema
            if resource.enable_load:
                logger.log(f"[4/5] LOAD - Loading data to core.{resource.target_table}...")
                data_loader = DataLoaderService()
                try:
                    # Read from staging file for LOAD (avoids keeping full list in RAM twice)
                    with open(staging_path, "r", encoding="utf-8") as f:
                        data_for_load = [json.loads(line) for line in f]
                    loaded_count = data_loader.load_data(
                        session=session,
                        dataset=dataset,
                        normalized_data=data_for_load,
                        load_mode=resource.load_mode or "upsert"
                    )
                    execution.records_loaded = loaded_count
                    logger.log(f"  Loaded {loaded_count} records")
                except Exception as e:
                    execution.error_message = f"Load failed: {str(e)}"
                    logger.log(f"  WARNING: Load failed: {e}")
            else:
                logger.log("[4/5] LOAD - Skipped (enable_load=False)")

            # 5. NOTIFY - Send webhooks
            logger.log("[5/5] NOTIFY - Sending notifications...")
            notification_service = NotificationService()
            notification_service.notify_subscribers(session, dataset)

            execution.status = "completed"
            execution.completed_at = datetime.utcnow()
            logger.log(f"COMPLETED - {total_records} records in {round((execution.completed_at - execution.started_at).total_seconds(), 1)}s")

            # Rebuild the dynamic GraphQL data schema so new data is immediately queryable
            try:
                from app.graphql_data import engine as data_engine
                count = data_engine.rebuild(session)
                logger.log(f"  GraphQL data schema rebuilt — {count} dataset(s) exposed.")
            except Exception as rebuild_err:
                logger.log(f"  WARNING: GraphQL data schema rebuild failed: {rebuild_err}")

        except Exception as e:
            execution.status = "failed"
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            logger.log(f"FAILED: {e}")
            raise

        finally:
            logger.close()
            session.commit()

        return dataset

    @staticmethod
    def _derive_dataset(session: Session, config: DerivedDatasetConfig, staging_path: str, logger: ExecutionLogger) -> int:
        """
        Extracts derived catalog entries from the staging JSONL file using natural key upsert.

        For each record, extracts key_field + extract_fields and upserts into derived_dataset_entry
        keyed by (config_id, key_value).  Returns the number of distinct entries processed.
        """
        from uuid import uuid4 as _uuid4
        from datetime import datetime as _dt

        target = config.target_name
        key_field = config.key_field
        extract_fields: list = config.extract_fields or []

        # Group by key_field — last write wins (most recent record for same key)
        extracted: dict[str, dict] = {}
        with open(staging_path, "r", encoding="utf-8") as f:
            for line in f:
                record = json.loads(line)
                key_val = record.get(key_field)
                if key_val is None:
                    continue
                entry: dict = {key_field: key_val}
                for field in extract_fields:
                    if field in record:
                        entry[field] = record[field]
                extracted[str(key_val)] = entry

        if not extracted:
            logger.log(f"  [{target}] No records with key_field '{key_field}' found — skipping")
            return 0

        logger.log(f"  [{target}] {len(extracted)} distinct '{key_field}' values found")

        if config.merge_strategy == "insert_only":
            # Only insert new keys, never overwrite
            for key_val, entry_data in extracted.items():
                existing = session.query(DerivedDatasetEntry).filter(
                    DerivedDatasetEntry.config_id == config.id,
                    DerivedDatasetEntry.key_value == key_val,
                ).first()
                if not existing:
                    session.add(DerivedDatasetEntry(
                        id=_uuid4(),
                        config_id=config.id,
                        key_value=key_val,
                        data=entry_data,
                        updated_at=_dt.utcnow(),
                    ))
        else:
            # upsert: merge existing entries
            for key_val, entry_data in extracted.items():
                existing = session.query(DerivedDatasetEntry).filter(
                    DerivedDatasetEntry.config_id == config.id,
                    DerivedDatasetEntry.key_value == key_val,
                ).first()
                if existing:
                    existing.data = entry_data
                    existing.updated_at = _dt.utcnow()
                else:
                    session.add(DerivedDatasetEntry(
                        id=_uuid4(),
                        config_id=config.id,
                        key_value=key_val,
                        data=entry_data,
                        updated_at=_dt.utcnow(),
                    ))

        session.flush()
        total = session.query(DerivedDatasetEntry).filter(
            DerivedDatasetEntry.config_id == config.id
        ).count()
        logger.log(f"  [{target}] Done — {len(extracted)} processed, {total} total entries in catalog")
        return len(extracted)

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