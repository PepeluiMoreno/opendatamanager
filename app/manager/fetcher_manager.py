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
from app.services.grouping import infer

LOG_DIR = "data/logs"

# Claves internas que no deben mostrarse en el título de ejecución
_INTERNAL_PARAM_KEYS = frozenset({
    "_resume_state", "_matched_urls", "_dimensions",
    "_staging_path", "_preview_limit", "_discover_mode",
    "_dataset_type",
})


def _execution_label(params: Optional[dict]) -> Optional[str]:
    """
    Genera un label legible a partir de los execution_params,
    excluyendo las claves internas (que contienen objetos o listas grandes).
    """
    if not params:
        return None
    visible = {
        k: v for k, v in params.items()
        if k not in _INTERNAL_PARAM_KEYS and not str(k).startswith("_")
    }
    if not visible:
        return None
    return ", ".join(f"{k}={v}" for k, v in visible.items())


class ExecutionLogger:
    """Writes timestamped log lines to a per-execution file and stdout."""

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
                    stale.completed_at = datetime.utcnow()
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
                        f"Resource hijo '{resource.name}' sin ResourceCandidate asociado."
                    )
                runtime_params["_matched_urls"] = list(candidate.matched_urls or [])
                runtime_params["_dimensions"] = list(candidate.dimensions or [])

            fetcher = FetcherFactory.create_from_resource(resource, runtime_params)

            # ── DISCOVER MODE ────────────────────────────────────────────────
            if not is_child and hasattr(fetcher, "discover"):
                logger.log("[1/1] DISCOVER — Crawleando árbol sin descargar ficheros...")
                leaf_urls = fetcher.discover()
                logger.log(f"  {len(leaf_urls)} URLs hoja descubiertas. Inferiendo agrupaciones...")

                # Profile stats generados por el fetcher (función pura)
                profile_stats = getattr(fetcher, "profile_stats", {})
                if profile_stats:
                    logger.log(
                        f"  Stats: {profile_stats.get('total_files')} ficheros | "
                        f"ext: {list(profile_stats.get('file_extensions', {}).keys())} | "
                        f"profundidad dominante: {profile_stats.get('dominant_depth')}"
                    )

                # path_root es opcional: si se pasa, sobreescribe el prefijo común
                # autodetectado. Útil cuando un crawler mezcla sub-portales.
                resource_params = {p.key: p.value for p in resource.params}
                path_root = resource_params.get("path_root") or None
                raw_proposals = infer(leaf_urls, path_root=path_root)
                logger.log(f"  {len(raw_proposals)} propuesta(s) de agrupación.")

                created_ids = []
                for p in raw_proposals:
                    pd = p if isinstance(p, dict) else p.to_dict()
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

                # Persistir artefacto: propuestas + profile_stats
                artifact = {
                    "proposals": [p if isinstance(p, dict) else p.to_dict() for p in raw_proposals],
                    "profile_stats": profile_stats,
                }
                artifact_path = os.path.join(staging_dir, f"discover_{execution.id}.json")
                with open(artifact_path, "w", encoding="utf-8") as f:
                    json.dump(artifact, f, ensure_ascii=False, indent=2)

                # Guardar profile_stats en execution_params (sin los campos internos grandes)
                safe_params = {
                    k: v for k, v in (execution_params or {}).items()
                    if k not in _INTERNAL_PARAM_KEYS
                }
                safe_params["_profile_stats"] = profile_stats
                execution.execution_params = safe_params
                execution.staging_path = artifact_path
                execution.total_records = len(raw_proposals)
                execution.active_seconds = (execution.active_seconds or 0) + int(
                    (datetime.utcnow() - period_start).total_seconds()
                )
                execution.status = "completed"
                execution.completed_at = datetime.utcnow()
                logger.log(
                    f"DISCOVER COMPLETED — {len(raw_proposals)} candidato(s) | "
                    f"{len(leaf_urls)} URLs | stats guardados"
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
                logger.log(f"  RESUME — continuing from {hint}")

            file_mode = "a" if is_resume else "w"
            total_records = int(execution.total_records or 0) if is_resume else 0
            paused = False
            _STAGING_EXCLUDE = {"raw_xml_content", "raw_html", "_raw"}

            _PAUSE_CHECK_EVERY = 50  # records dentro de un chunk
            with open(staging_path, file_mode, encoding="utf-8") as f:
                for chunk in fetcher.stream():
                    written_in_chunk = 0
                    for record in chunk:
                        clean = {k: v for k, v in record.items() if k not in _STAGING_EXCLUDE}
                        serializable = FetcherManager._make_serializable(clean)
                        f.write(json.dumps(serializable, ensure_ascii=False) + "\n")
                        written_in_chunk += 1
                        if written_in_chunk % _PAUSE_CHECK_EVERY == 0:
                            f.flush()
                            session.refresh(execution)
                            if execution.pause_requested:
                                total_records += written_in_chunk
                                execution.total_records = total_records
                                session.commit()
                                paused = True
                                logger.log(f"  Pause requested — stopping mid-chunk at {total_records} records")
                                break
                    if paused:
                        break
                    total_records += written_in_chunk
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
                current_params = {
                    k: v for k, v in (execution.execution_params or {}).items()
                    if k not in _INTERNAL_PARAM_KEYS
                }
                current_params["_resume_state"] = resume_state
                execution.execution_params = current_params
                execution.status = "paused"
                execution.completed_at = datetime.utcnow()
                logger.log(f"PAUSED — {total_records} records staged.")
                session.commit()
                logger.close()
                return None

            execution.staging_path = staging_path
            session.commit()
            logger.log(f"  Done: {total_records} records → {staging_path}")

            logger.log("[2/5] DATASET - Building dataset...")
            dataset_builder = DatasetBuilder()
            dataset = dataset_builder.build(
                session=session, resource=resource, execution=execution,
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
                logger.log("[3/5] DERIVE - Skipped")

            if resource.enable_load:
                logger.log(f"[4/5] LOAD - Loading data to core.{resource.target_table}...")
                data_loader = DataLoaderService()
                try:
                    with open(staging_path, "r", encoding="utf-8") as f:
                        data_for_load = [json.loads(line) for line in f]
                    loaded_count = data_loader.load_data(
                        session=session, dataset=dataset,
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
                logger.log("[4/5] LOAD - Skipped")

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
                logger.log(f"  GraphQL data schema rebuilt — {count} dataset(s).")
            except Exception as rebuild_err:
                logger.log(f"  WARNING: GraphQL rebuild failed: {rebuild_err}")

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
            logger.log(f"  [{target}] No records with key_field '{key_field}' — skipping")
            return 0

        logger.log(f"  [{target}] {len(extracted)} distinct '{key_field}' values")

        if config.merge_strategy == "insert_only":
            for key_val, entry_data in extracted.items():
                existing = session.query(DerivedDatasetEntry).filter(
                    DerivedDatasetEntry.config_id == config.id,
                    DerivedDatasetEntry.key_value == key_val,
                ).first()
                if not existing:
                    session.add(DerivedDatasetEntry(id=_uuid4(), config_id=config.id, key_value=key_val, data=entry_data, updated_at=_dt.utcnow()))
        else:
            for key_val, entry_data in extracted.items():
                existing = session.query(DerivedDatasetEntry).filter(
                    DerivedDatasetEntry.config_id == config.id,
                    DerivedDatasetEntry.key_value == key_val,
                ).first()
                if existing:
                    existing.data = entry_data; existing.updated_at = _dt.utcnow()
                else:
                    session.add(DerivedDatasetEntry(id=_uuid4(), config_id=config.id, key_value=key_val, data=entry_data, updated_at=_dt.utcnow()))

        session.flush()
        total = session.query(DerivedDatasetEntry).filter(DerivedDatasetEntry.config_id == config.id).count()
        logger.log(f"  [{target}] Done — {len(extracted)} processed, {total} total entries")
        return len(extracted)

    @staticmethod
    def run_all(session: Session) -> None:
        resources = session.query(Resource).filter(Resource.active == True).all()
        if not resources:
            print("No hay resources activos")
            return
        for resource in resources:
            try:
                FetcherManager.run(session, str(resource.id))
            except Exception as e:
                print(f"Error en '{resource.name}': {e}")

    @staticmethod
    def fetch_only(session: Session, resource_id: str, limit: int = 10, runtime_params: dict = None) -> list:
        resource = session.query(Resource).filter(Resource.id == resource_id).first()
        if not resource:
            raise ValueError(f"Resource con id '{resource_id}' no encontrado")
        if not resource.active:
            return []
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
            raise ValueError(f"Unexpected data type: {type(data)}")
        serializable_data = [FetcherManager._make_serializable(item) for item in data_list]
        return serializable_data[:limit]
