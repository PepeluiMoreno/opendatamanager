"""
Manager para ejecutar fetchers y actualizar datos en BD.
"""
import os
import json
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.models import Resource, ResourceCandidate, ResourceExecution, Dataset, DerivedDatasetConfig, DerivedDatasetEntry
from app.fetchers.factory import FetcherFactory
from app.builders.dataset_builder import DatasetBuilder
from app.services.notification_service import NotificationService
from app.services.data_loader_service import DataLoaderService
from app.services.grouping_inferer import get_inferer

LOG_DIR = "data/logs"


class ExecutionLogger:
    """Writes timestamped log lines to a per-execution file and stdout.
    Also captures Python logging records from the 'app.fetchers' hierarchy."""

    def __init__(self, execution_id: str):
        os.makedirs(LOG_DIR, exist_ok=True)
        self.log_path = f"{LOG_DIR}/{execution_id}.log"
        self._file = open(self.log_path, "a", buffering=1)
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
        from bs4 import BeautifulSoup, Tag
        from bs4.element import NavigableString
        if isinstance(obj, dict):
            return {k: FetcherManager._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [FetcherManager._make_serializable(item) for item in obj]
        elif isinstance(obj, (BeautifulSoup, Tag)):
            return str(obj)
        elif isinstance(obj, NavigableString):
            return str(obj)
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        else:
            return str(obj)

    @staticmethod
    def run(session: Session, resource_id: str, execution_params: Optional[dict] = None, execution_id: Optional[str] = None) -> Optional[Dataset]:
        resource = session.query(Resource).filter(Resource.id == resource_id).first()

        if not resource:
            raise ValueError(f"Resource con id '{resource_id}' no encontrado")

        if not resource.active:
            print(f"Resource '{resource.name}' está desactivado, omitiendo...")
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

        if execution_id:
            execution = session.query(ResourceExecution).filter(
                ResourceExecution.id == execution_id
            ).first()
            if not execution:
                raise ValueError(f"Execution '{execution_id}' not found")
        else:
            execution = ResourceExecution(
                resource_id=resource_id,
                resource_name=resource.name,
                status="running",
                started_at=datetime.utcnow(),
                execution_params=execution_params,
            )
            session.add(execution)
            session.commit()

        period_start = datetime.utcnow()
        logger = ExecutionLogger(str(execution.id))
        try:
            logger.log(f"Ejecutando Resource: {resource.name} (publisher: {resource.publisher})")

            staging_dir = f"data/staging/{resource_id}"
            os.makedirs(staging_dir, exist_ok=True)
            staging_path = os.path.join(staging_dir, f"{execution.id}.jsonl")

            saved_state = (execution.execution_params or {}).get("_resume_state")
            is_resume = bool(saved_state)

            runtime_params = dict(execution_params or {})
            runtime_params["_staging_path"] = staging_path
            if saved_state:
                runtime_params["_resume_state"] = saved_state

            is_child = resource.parent_resource_id is not None

            if is_child:
                candidate = (
                    session.query(ResourceCandidate)
                    .filter(
                        ResourceCandidate.promoted_resource_id == resource.id,
                        ResourceCandidate.deleted_at.is_(None),
                    )
                    .order_by(ResourceCandidate.detected_at.desc())
                    .first()
                )
                if not candidate:
                    raise RuntimeError(
                        f"Resource hijo '{resource.name}' sin ResourceCandidate asociado "
                        f"(promoted_resource_id={resource.id})."
                    )
                runtime_params["_matched_urls"] = list(candidate.matched_urls or [])
                runtime_params["_dimensions"] = list(candidate.dimensions or [])

            fetcher = FetcherFactory.create_from_resource(resource, runtime_params)

            # ── DISCOVER MODE ────────────────────────────────────────────────
            if not is_child and hasattr(fetcher, "discover"):
                logger.log("[1/1] DISCOVER — Crawleando árbol sin descargar ficheros...")
                leaf_urls = fetcher.discover()
                logger.log(f"  {len(leaf_urls)} URLs hoja descubiertas. Inferiendo agrupaciones...")

                # Elegir inferer según parámetro del resource (default: 'generic')
                resource_params = {p.key: p.value for p in resource.params}
                inferer_name = resource_params.get("grouping_inferer", "generic")
                try:
                    inferer = get_inferer(inferer_name)
                except ValueError as e:
                    logger.log(f"  WARN: {e} — usando 'generic'")
                    inferer = get_inferer("generic")

                logger.log(f"  Inferer seleccionado: '{inferer_name}' ({inferer.__class__.__name__})")
                raw_proposals = inferer.infer(leaf_urls)
                logger.log(f"  {len(raw_proposals)} propuesta(s) de agrupación. Persistiendo candidatos...")

                created_ids = []
                for p in raw_proposals:
                    # raw_proposals puede ser dataclasses o dicts según el inferer
                    if isinstance(p, dict):
                        pd = p
                    else:
                        from dataclasses import asdict
                        pd = asdict(p)

                    candidate = ResourceCandidate(
                        execution_id=execution.id,
                        crawler_resource_id=resource.id,
                        path_template=pd.get("path_template"),
                        dimensions=pd.get("dimensions"),
                        matched_urls=pd.get("matched_urls"),
                        file_types=pd.get("file_types"),
                        suggested_name=pd.get("suggested_name"),
                        confidence=pd.get("confidence"),
                        status="discovered",
                    )
                    session.add(candidate)
                    session.flush()
                    created_ids.append(str(candidate.id))

                artifact_path = os.path.join(staging_dir, f"discover_{execution.id}.json")
                with open(artifact_path, "w", encoding="utf-8") as f:
                    json.dump(
                        [p if isinstance(p, dict) else p.to_dict() for p in raw_proposals],
                        f, ensure_ascii=False, indent=2,
                    )
                execution.staging_path = artifact_path
                execution.total_records = len(raw_proposals)
                execution.active_seconds = (execution.active_seconds or 0) + int(
                    (datetime.utcnow() - period_start).total_seconds()
                )
                execution.status = "completed"
                execution.completed_at = datetime.utcnow()
                logger.log(
                    f"DISCOVER COMPLETED — {len(raw_proposals)} candidato(s) creados; "
                    f"{len(leaf_urls)} URLs analizadas"
                )
                session.commit()
                logger.close()
                return None

            # ── STREAM MODE ──────────────────────────────────────────────────
            logger.log("[1/5] EXTRACT+STAGE - Streaming data to staging file...")
            if is_resume:
                hint = (
                    f"pivot {saved_state['pivot_index']}" if "pivot_index" in saved_state else
                    f"page {saved_state['pages_fetched']}" if "pages_fetched" in saved_state else
                    f"page {saved_state['page']}" if "page" in saved_state else
                    "saved state"
                )
                logger.log(f"  RESUME — continuing from {hint}, appending to existing staging file")

            file_mode = "a" if is_resume else "w"
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

                    session.refresh(execution)
                    if execution.pause_requested:
                        paused = True
                        logger.log(f"  Pause requested — stopping at {total_records} records")
                        break

            if paused:
                execution.active_seconds = (execution.active_seconds or 0) + int((datetime.utcnow() - period_start).total_seconds())
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

            logger.log("[2/5] DATASET - Building dataset...")
            dataset_builder = DatasetBuilder()
            dataset = dataset_builder.build(
                session=session,
                resource=resource,
                execution=execution,
            )
            session.add(dataset)
            logger.log(f"  Dataset created: {dataset.version_string}")

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

            if resource.enable_load:
                logger.log(f"[4/5] LOAD - Loading data to core.{resource.target_table}...")
                data_loader = DataLoaderService()
                try:
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

            logger.log("[5/5] NOTIFY - Sending notifications...")
            notification_service = NotificationService()
            notification_service.notify_subscribers(session, dataset)

            execution.active_seconds = (execution.active_seconds or 0) + int((datetime.utcnow() - period_start).total_seconds())
            execution.status = "completed"
            execution.completed_at = datetime.utcnow()
            logger.log(f"COMPLETED - {total_records} records in {execution.active_seconds}s active")

            try:
                if os.path.exists(staging_path):
                    os.remove(staging_path)
                staging_dir_clean = os.path.dirname(staging_path)
                if os.path.isdir(staging_dir_clean) and not any(os.scandir(staging_dir_clean)):
                    os.rmdir(staging_dir_clean)
            except OSError:
                pass

            try:
                from app.graphql_data import engine as data_engine
                session.flush()
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
        from uuid import uuid4 as _uuid4
        from datetime import datetime as _dt

        target = config.target_name
        key_field = config.key_field
        extract_fields: list = config.extract_fields or []

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
        resource = session.query(Resource).filter(Resource.id == resource_id).first()
        if not resource:
            raise ValueError(f"Resource con id '{resource_id}' no encontrado")
        if not resource.active:
            print(f"Resource '{resource.name}' está desactivado, omitiendo...")
            return []
        print(f"Extracting data from: {resource.name} (limit: {limit})")
        fetcher = FetcherFactory.create_from_resource(resource)
        if runtime_params:
            for k, v in runtime_params.items():
                if v not in (None, ""):
                    fetcher.params[k] = v
        fetcher.params["_preview_limit"] = limit
        data = fetcher.execute()
        if isinstance(data, dict):
            data_list = [data]
        elif isinstance(data, list):
            data_list = data
        else:
            raise ValueError(f"Unexpected data type from fetcher: {type(data)}")
        serializable_data = [FetcherManager._make_serializable(item) for item in data_list]
        limited_data = serializable_data[:limit]
        print(f"  Extracted {len(limited_data)} records (limited from {len(data_list)})")
        return limited_data
