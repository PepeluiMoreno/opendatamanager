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
            # Si ya se creó un registro de ejecución, marcarlo como abortado
            if execution_id:
                stale = session.query(ResourceExecution).filter(
                    ResourceExecution.id == execution_id,
                    ResourceExecution.status == "running",
                ).first()
                if stale:
                    stale.status = "failed"
                    stale.completed_at = __import__("datetime").datetime.utcnow()
                    stale.error_message = "Resource desactivado al lanzar la ejecución"
                    session.commit()
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
                resource_name=resource.name,  # snapshot histórico: no cambia si se renombra el resource
                status="running",
                started_at=datetime.utcnow(),
                execution_params=execution_params,
            )
            session.add(execution)
            session.commit()  # Commit immediately so execution is visible as "running"

        period_start = datetime.utcnow()  # defined before try so except can always reference it
        logger = ExecutionLogger(str(execution.id))
        try:
            logger.log(f"Ejecutando Resource: {resource.name} (publisher: {resource.publisher})")

            # 1. EXTRACT + STAGE (streaming — one page written to disk at a time)
            staging_dir = f"data/staging/{resource_id}"
            os.makedirs(staging_dir, exist_ok=True)
            staging_path = os.path.join(staging_dir, f"{execution.id}.jsonl")

            # Detect resume: execution_params may carry _resume_state saved at pause time
            saved_state = (execution.execution_params or {}).get("_resume_state")
            is_resume   = bool(saved_state)

            # Build runtime params for the fetcher, injecting resume info if needed
            runtime_params = dict(execution_params or {})
            runtime_params["_staging_path"] = staging_path
            if saved_state:
                runtime_params["_resume_state"] = saved_state

            # ── DISCOVER MODE ────────────────────────────────────────────────
            discover_mode = runtime_params.get("_discover_mode", False)
            if discover_mode and hasattr(fetcher, "discover"):
                logger.log("[1/1] DISCOVER — Crawling sections without downloading files...")
                sections = fetcher.discover()
                artifact_path = os.path.join(staging_dir, f"discover_{execution.id}.json")
                with open(artifact_path, "w", encoding="utf-8") as f:
                    json.dump(sections, f, ensure_ascii=False, indent=2)
                execution.staging_path = artifact_path
                execution.total_records = len(sections)
                execution.active_seconds = (execution.active_seconds or 0) + int(
                    (datetime.utcnow() - period_start).total_seconds()
                )
                execution.status = "completed"
                execution.completed_at = datetime.utcnow()
                logger.log(f"DISCOVER COMPLETED — {len(sections)} sections → {artifact_path}")
                session.commit()
                logger.close()
                return None

            logger.log("[1/5] EXTRACT+STAGE - Streaming data to staging file...")
            if is_resume:
                hint = (
                    f"pivot {saved_state['pivot_index']}" if "pivot_index" in saved_state else
                    f"page {saved_state['pages_fetched']}" if "pages_fetched" in saved_state else
                    f"page {saved_state['page']}" if "page" in saved_state else
                    "saved state"
                )
                logger.log(f"  RESUME — continuing from {hint}, appending to existing staging file")
            fetcher = FetcherFactory.create_from_resource(resource, runtime_params)

            # On resume, append to existing staging and recover already-staged record count
            file_mode    = "a" if is_resume else "w"
            total_records = int(execution.total_records or 0) if is_resume else 0
            paused = False
            _STAGING_EXCLUDE = {"raw_xml_content", "raw_html", "_raw"}

            with open(staging_path, file_mode, encoding="utf-8") as f:
                for chunk in fetcher.stream():
                    for record in chunk:
                        clean = {k: v for k, v in record.items() if k not in _STAGING_EXCLUDE}
                        serializable = FetcherManager._make_serializable(clean)
                        f.write(json.dumps(serializable, ensure_ascii=False) + "\n")
                    total_records += len(chunk)
                    execution.total_records = total_records
                    session.commit()
                    logger.log(f"  Staged {total_records} records so far...")

                    # Check cooperative pause signal
                    session.refresh(execution)
                    if execution.pause_requested:
                        paused = True
                        logger.log(f"  Pause requested — stopping at {total_records} records")
                        break

            if paused:
                # Accumulate active time for this period
                execution.active_seconds = (execution.active_seconds or 0) + int((datetime.utcnow() - period_start).total_seconds())

                # Persist resume state from fetcher so next resume continues from here
                resume_state = getattr(fetcher, "current_state", {})
                current_params = dict(execution.execution_params or {})
                current_params["_resume_state"] = resume_state
                execution.execution_params = current_params
                execution.status = "paused"
                execution.completed_at = datetime.utcnow()
                if resume_state.get("pivot_index") is not None:
                    next_hint = f" (next: pivot {resume_state['pivot_index']})"
                elif resume_state.get("pages_fetched") is not None:
                    next_hint = f" (next: page {resume_state['pages_fetched'] + 1})"
                elif resume_state.get("page") is not None:
                    next_hint = f" (next: page {resume_state['page']})"
                else:
                    next_hint = ""
                logger.log(f"PAUSED — {total_records} records staged{next_hint}. Resume to continue.")
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
                        load_mode=resource.load_mode or "upsert",
                        table_name=f"core.{resource.target_table}",
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

            execution.active_seconds = (execution.active_seconds or 0) + int((datetime.utcnow() - period_start).total_seconds())
            execution.status = "completed"
            execution.completed_at = datetime.utcnow()
            logger.log(f"COMPLETED - {total_records} records in {execution.active_seconds}s active")

            # Staging file no longer needed — dataset and load steps already consumed it
            try:
                if os.path.exists(staging_path):
                    os.remove(staging_path)
                staging_dir = os.path.dirname(staging_path)
                if os.path.isdir(staging_dir) and not any(os.scandir(staging_dir)):
                    os.rmdir(staging_dir)
            except OSError:
                pass

            # Rebuild the dynamic GraphQL data schema so new data is immediately queryable
            try:
                from app.graphql_data import engine as data_engine
                session.flush()  # Ensure new dataset is visible to build_schema query (autoflush=False)
                count = data_engine.rebuild(session)
                logger.log(f"  GraphQL data schema rebuilt — {count} dataset(s) total in data API.")
            except Exception as rebuild_err:
                logger.log(f"  WARNING: GraphQL data schema rebuild failed: {rebuild_err}")

        except Exception as e:
            execution.active_seconds = (execution.active_seconds or 0) + int((datetime.utcnow() - period_start).total_seconds())
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
    def fetch_only(session: Session, resource_id: str, limit: int = 10, runtime_params: dict = None) -> list:
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
        # Inject runtime overrides (external params defined at sandbox time)
        if runtime_params:
            for k, v in runtime_params.items():
                if v not in (None, ""):
                    fetcher.params[k] = v
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