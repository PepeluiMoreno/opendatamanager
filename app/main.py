"""
Servidor principal FastAPI + Strawberry GraphQL.

Ejecutar con:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8040
"""
import os
import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from strawberry.fastapi import GraphQLRouter
from app.graphql.schema import schema
from app.database import SessionLocal
from app.models import Dataset, Resource, ResourceExecution
from app.services.scheduler_service import SchedulerService
from app.manager.fetcher_manager import LOG_DIR
from app.graphql_data import engine as data_engine
from app.graphql_data.router import router as data_router

# Crear aplicación FastAPI
app = FastAPI(
    title="OpenDataManager API",
    description="API GraphQL para gestión de fuentes de datos OpenData",
    version="1.0.0"
)

scheduler_service = SchedulerService()

@app.on_event("startup")
async def startup_event():
    import asyncio

    scheduler_service.start()

    async def _init_with_db():
        """Espera a que la BD esté disponible y luego inicializa jobs y schema."""
        for attempt in range(15):
            try:
                scheduler_service.add_resource_jobs()
                db = SessionLocal()
                try:
                    data_engine.rebuild(db)
                finally:
                    db.close()
                print("[startup] BD disponible — scheduler y schema GraphQL inicializados.")
                return
            except Exception as e:
                wait = min(2 ** attempt, 30)
                print(f"[startup] BD no disponible (intento {attempt+1}/15): {type(e).__name__} — reintentando en {wait}s")
                await asyncio.sleep(wait)
        print("[startup] WARN: BD inaccesible tras 15 intentos. Scheduler y schema GraphQL no inicializados.")

    # Lanzar en background para que el servidor arranque aunque la BD tarde
    asyncio.ensure_future(_init_with_db())

@app.on_event("shutdown")
async def shutdown_event():
    scheduler_service.shutdown()

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurar router GraphQL (gestión — Strawberry)
graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")

# Configurar router GraphQL de datos (dinámico — graphql-core)
app.include_router(data_router, prefix="/graphql/data", tags=["GraphQL Data API"])


@app.get("/")
def root():
    return {
        "name": "OpenDataManager API",
        "version": "1.0.0",
        "graphql_management": "/graphql",
        "graphql_data": "/graphql/data",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/api/version")
def app_version():
    return {"version": os.environ.get("APP_VERSION", "dev")}


@app.get("/api/graphql-data/registry")
async def graphql_data_registry():
    """Lista todos los datasets expuestos en la API GraphQL dinámica (/graphql/data)."""
    return data_engine.get_registry()


@app.get("/api/datasets/tree")
async def datasets_tree():
    """Devuelve todos los datasets agrupados por resource, con versiones ordenadas desc."""
    from app.models import Resource as ResourceModel
    session = SessionLocal()
    try:
        registry_by_id = {e["datasetId"]: e for e in data_engine.get_registry() if "datasetId" in e}

        resources = (
            session.query(ResourceModel)
            .filter(ResourceModel.deleted_at == None)
            .order_by(ResourceModel.name)
            .all()
        )

        from collections import OrderedDict

        tree = []
        for res in resources:
            datasets_for_res = (
                session.query(Dataset)
                .filter(Dataset.resource_id == res.id)
                .filter(Dataset.deleted_at == None)
                .order_by(Dataset.created_at.desc())
                .all()
            )
            if not datasets_for_res:
                continue

            resource_params = {p.key: p.value for p in res.params}

            groups: OrderedDict = OrderedDict()
            for ds in datasets_for_res:
                groups.setdefault(ds.label, []).append(ds)

            for label, ds_list in groups.items():
                versions = []
                for ds in ds_list:
                    ds_id = str(ds.id)
                    exec_params = ds.execution.execution_params if ds.execution else None
                    versions.append({
                        "datasetId": ds_id,
                        "version": f"{ds.major_version}.{ds.minor_version}.{ds.patch_version}",
                        "recordCount": ds.record_count,
                        "createdAt": ds.created_at.isoformat() if ds.created_at else None,
                        "executionParams": exec_params,
                        "isLatest": ds_id in registry_by_id,
                        "queryName": registry_by_id.get(ds_id, {}).get("queryName"),
                        "fields": registry_by_id.get(ds_id, {}).get("fields", []),
                    })

                display_name = f"{res.name} · {label}" if label else res.name

                tree.append({
                    "nodeId": f"{res.id}::{label or ''}",
                    "resourceId": str(res.id),
                    "resourceName": res.name,
                    "displayName": display_name,
                    "label": label,
                    "targetTable": res.target_table,
                    "active": res.active,
                    "resourceParams": resource_params,
                    "versions": versions,
                })

        tree.sort(key=lambda n: n["displayName"].lower())
        return tree
    finally:
        session.close()


def _hard_delete_dataset_files(data_path: str) -> None:
    """Borra el JSONL y schema.json del dataset si existen."""
    if data_path and os.path.exists(data_path):
        try:
            os.remove(data_path)
        except OSError:
            pass
        dataset_dir = os.path.dirname(data_path)
        schema_path = os.path.join(dataset_dir, "schema.json")
        if os.path.exists(schema_path):
            try:
                os.remove(schema_path)
            except OSError:
                pass


def _rebuild_data_api() -> None:
    db2 = SessionLocal()
    try:
        data_engine.rebuild(db2)
    finally:
        db2.close()


@app.delete("/api/datasets/{dataset_id}")
async def delete_dataset(dataset_id: str, hard: bool = False):
    """Borra un dataset.
    - hard=False (default): soft-delete (deleted_at = now), va a Trash, restaurable.
    - hard=True: borra registro de BD + fichero JSONL irreversiblemente.
    """
    from datetime import datetime
    session = SessionLocal()
    try:
        dataset = session.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        data_path = dataset.data_path
        if hard:
            session.delete(dataset)
            session.commit()
            _hard_delete_dataset_files(data_path)
        else:
            dataset.deleted_at = datetime.utcnow()
            session.commit()
        _rebuild_data_api()
        return {"ok": True, "hard": hard}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@app.post("/api/datasets/{dataset_id}/restore")
async def restore_dataset(dataset_id: str):
    """Restaura un dataset soft-borrado (deleted_at → null)."""
    session = SessionLocal()
    try:
        dataset = session.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        if dataset.deleted_at is None:
            return {"ok": True, "alreadyActive": True}
        dataset.deleted_at = None
        session.commit()
        _rebuild_data_api()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@app.get("/api/resources/{resource_id}/datasets/summary")
async def resource_datasets_summary(resource_id: str):
    """Resumen de los datasets activos (no borrados) de un recurso, para usar en
    la modal de cascada-delete: cuántos hay, cuántos registros y cuánto pesan en disco."""
    session = SessionLocal()
    try:
        rows = (
            session.query(Dataset)
            .filter(Dataset.resource_id == resource_id)
            .filter(Dataset.deleted_at == None)
            .all()
        )
        total_bytes = 0
        for ds in rows:
            if ds.data_path and os.path.exists(ds.data_path):
                try:
                    total_bytes += os.path.getsize(ds.data_path)
                except OSError:
                    pass
        return {
            "count": len(rows),
            "totalRecords": sum((ds.record_count or 0) for ds in rows),
            "diskBytes": total_bytes,
        }
    finally:
        session.close()


@app.delete("/api/resources/{resource_id}/datasets")
async def delete_resource_datasets(resource_id: str, hard: bool = False):
    """Cascada: borra todos los datasets activos de un recurso.
    - hard=False (default): soft-delete de cada uno.
    - hard=True: borra registros + JSONLs.
    El recurso y el historial de ResourceExecution permanecen intactos."""
    from datetime import datetime
    session = SessionLocal()
    try:
        rows = (
            session.query(Dataset)
            .filter(Dataset.resource_id == resource_id)
            .filter(Dataset.deleted_at == None)
            .all()
        )
        affected = len(rows)
        if hard:
            paths = [ds.data_path for ds in rows]
            for ds in rows:
                session.delete(ds)
            session.commit()
            for p in paths:
                _hard_delete_dataset_files(p)
        else:
            now = datetime.utcnow()
            for ds in rows:
                ds.deleted_at = now
            session.commit()
        _rebuild_data_api()
        return {"ok": True, "hard": hard, "affected": affected}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@app.get("/api/datasets/trash")
async def datasets_trash():
    """Lista todos los datasets soft-borrados, para la pestaña Trash."""
    session = SessionLocal()
    try:
        rows = (
            session.query(Dataset)
            .filter(Dataset.deleted_at != None)
            .order_by(Dataset.deleted_at.desc())
            .all()
        )
        result = []
        for ds in rows:
            res = ds.resource
            result.append({
                "datasetId": str(ds.id),
                "resourceId": str(ds.resource_id),
                "resourceName": res.name if res else None,
                "version": f"{ds.major_version}.{ds.minor_version}.{ds.patch_version}",
                "label": ds.label,
                "recordCount": ds.record_count,
                "createdAt": ds.created_at.isoformat() if ds.created_at else None,
                "deletedAt": ds.deleted_at.isoformat() if ds.deleted_at else None,
            })
        return result
    finally:
        session.close()


@app.get("/api/datasets/{dataset_id}/data.jsonl")
async def download_dataset_data(dataset_id: str):
    session = SessionLocal()
    try:
        dataset = session.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        if not os.path.exists(dataset.data_path):
            raise HTTPException(status_code=404, detail="Data file not found")
        return FileResponse(dataset.data_path, media_type="application/x-ndjson")
    finally:
        session.close()


@app.get("/api/datasets/{dataset_id}/schema.json")
async def download_dataset_schema(dataset_id: str):
    session = SessionLocal()
    try:
        dataset = session.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        dataset_dir = os.path.dirname(dataset.data_path)
        schema_path = f"{dataset_dir}/schema.json"
        if not os.path.exists(schema_path):
            raise HTTPException(status_code=404, detail="Schema file not found")
        return FileResponse(schema_path, media_type="application/json")
    finally:
        session.close()


@app.get("/api/datasets/{dataset_id}/models.py")
async def download_dataset_models(dataset_id: str):
    session = SessionLocal()
    try:
        dataset = session.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        dataset_dir = os.path.dirname(dataset.data_path)
        models_path = f"{dataset_dir}/models.py"
        if not os.path.exists(models_path):
            raise HTTPException(status_code=404, detail="Models file not found")
        return FileResponse(models_path, media_type="text/x-python")
    finally:
        session.close()


@app.get("/api/datasets/{dataset_id}/metadata.json")
async def download_dataset_metadata(dataset_id: str):
    session = SessionLocal()
    try:
        dataset = session.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        dataset_dir = os.path.dirname(dataset.data_path)
        metadata_path = f"{dataset_dir}/metadata.json"
        if not os.path.exists(metadata_path):
            raise HTTPException(status_code=404, detail="Metadata file not found")
        return FileResponse(metadata_path, media_type="application/json")
    finally:
        session.close()


@app.get("/api/system/info")
async def system_info():
    """Returns host hardware info for the frontend status panel.
    Always reads from /proc/meminfo (host values visible inside Docker) so that
    ram_total and ram_available are consistent with each other.
    """
    import psutil
    cpu_logical = psutil.cpu_count(logical=True)
    cpu_physical = psutil.cpu_count(logical=False) or cpu_logical

    # /proc/meminfo inside Docker reflects host RAM — use it for both values
    # so they are always consistent (cgroup limit ≠ host available → confusing display).
    meminfo = {}
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                k, v = line.split(":", 1)
                meminfo[k.strip()] = int(v.strip().split()[0])  # kB
    except Exception:
        pass

    ram_total_mb  = round(meminfo.get("MemTotal",  0) / 1024)
    ram_avail_mb  = round(meminfo.get("MemAvailable", 0) / 1024)

    return {
        "ram_total_mb": ram_total_mb,
        "ram_available_mb": ram_avail_mb,
        "ram_total_gb": round(ram_total_mb / 1024, 1),
        "cpu_logical": cpu_logical,
        "cpu_physical": cpu_physical,
        "source": "host",
    }


@app.get("/api/system/concurrency")
async def system_concurrency():
    """Returns live thread and execution stats for the concurrency panel."""
    import threading
    from app.models import ResourceExecution

    threads = threading.enumerate()
    thread_list = [
        {"name": t.name, "daemon": t.daemon, "alive": t.is_alive()}
        for t in threads
    ]
    worker_threads = [t for t in threads if t.daemon and t.name.startswith("Thread-")]

    db = SessionLocal()
    try:
        running = db.query(ResourceExecution).filter(
            ResourceExecution.status == "running",
            ResourceExecution.deleted_at == None,
        ).count()
    finally:
        db.close()

    try:
        import psutil, os
        proc = psutil.Process(os.getpid())
        mem = proc.memory_info()
        mem_rss_mb = round(mem.rss / 1024 / 1024, 1)
        mem_vms_mb = round(mem.vms / 1024 / 1024, 1)
    except Exception:
        mem_rss_mb = None
        mem_vms_mb = None

    try:
        vm = psutil.virtual_memory()
        cgroup_limit_mb = None
        for path in ("/sys/fs/cgroup/memory/memory.limit_in_bytes", "/sys/fs/cgroup/memory.max"):
            try:
                with open(path) as f:
                    val = f.read().strip()
                if val not in ("max", ""):
                    limit_bytes = int(val)
                    if limit_bytes < 2 ** 62:
                        cgroup_limit_mb = round(limit_bytes / 1024 / 1024)
                        break
            except Exception:
                pass
        ram_total_mb = cgroup_limit_mb if cgroup_limit_mb else round(vm.total / 1024 / 1024)
    except Exception:
        ram_total_mb = None

    return {
        "total_threads": len(threads),
        "worker_threads": len(worker_threads),
        "running_executions": running,
        "threads": thread_list,
        "process_mem_rss_mb": mem_rss_mb,
        "process_mem_vms_mb": mem_vms_mb,
        "ram_total_mb": ram_total_mb,
    }


@app.get("/api/stats/resources")
async def resource_stats():
    """Per-resource extraction statistics: records extracted, trends, run history."""
    from sqlalchemy import func
    db = SessionLocal()
    try:
        resources = db.query(Resource).order_by(Resource.name).all()
        result = []
        for res in resources:
            # All executions (including soft-deleted) — used for immutable stats so
            # that deleting a failed run from the UI does not change success_rate.
            all_execs = (
                db.query(ResourceExecution)
                .filter(ResourceExecution.resource_id == res.id)
                .order_by(ResourceExecution.started_at.desc())
                .all()
            )
            # Visible (non-deleted) executions — used only for "last run" display.
            visible_execs = [e for e in all_execs if e.deleted_at is None]

            completed = [e for e in all_execs if e.status == "completed"]
            last = visible_execs[0] if visible_execs else None

            last_records = completed[0].total_records if completed else None
            prev_records = completed[1].total_records if len(completed) > 1 else None
            total_extracted = sum(e.total_records or 0 for e in completed)

            trend = None
            if last_records is not None and prev_records is not None:
                trend = last_records - prev_records

            # Resolve bounding_field label (used for bounding_value display)
            bounding_field = next(
                (p.value for p in res.params if p.key == "bounding_field"), None
            ) if res.params else None

            result.append({
                "resource_id": str(res.id),
                "resource_name": res.name,
                "publisher": res.publisher,
                "active": res.active,
                "total_executions": len(all_execs),
                "successful_executions": len(completed),
                "failed_executions": len([e for e in all_execs if e.status == "failed"]),
                "last_run": last.started_at.isoformat() if last else None,
                "last_status": last.status if last else None,
                "last_duration_s": (
                    round((last.completed_at - last.started_at).total_seconds())
                    if last and last.completed_at and last.started_at else None
                ),
                "last_records": last_records,
                "prev_records": prev_records,
                "trend": trend,
                "total_records_extracted": total_extracted,
                # External params used in the last visible execution
                "last_execution_params": last.execution_params if last else None,
                "bounding_field": bounding_field,
            })
        return result
    finally:
        db.close()


@app.get("/api/executions/{execution_id}/logs")
async def get_execution_logs(
    execution_id: str,
    lines: int = Query(default=100, ge=1, le=5000),
    filter: str = Query(default=""),
    since: int = Query(default=0, description="Minutes back (0=all)"),
    follow: bool = Query(default=False),
):
    """Stream or fetch logs for a given execution. follow=true → SSE."""
    log_path = f"{LOG_DIR}/{execution_id}.log"

    def read_filtered(path: str) -> list[str]:
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
        if since > 0:
            cutoff = datetime.utcnow() - timedelta(minutes=since)
            def ts_ok(line: str) -> bool:
                # lines start with [HH:MM:SS]
                try:
                    t = datetime.strptime(line[1:9], "%H:%M:%S")
                    now = datetime.utcnow()
                    t = t.replace(year=now.year, month=now.month, day=now.day)
                    return t >= cutoff
                except Exception:
                    return True
            all_lines = [l for l in all_lines if ts_ok(l)]
        if filter:
            all_lines = [l for l in all_lines if filter.lower() in l.lower()]
        return all_lines[-lines:]

    if follow:
        async def event_stream():
            last_pos = os.path.getsize(log_path) if os.path.exists(log_path) else 0
            max_seconds = 600
            waited = 0
            while waited < max_seconds:
                if os.path.exists(log_path):
                    with open(log_path, "r", encoding="utf-8") as f:
                        f.seek(last_pos)
                        chunk = f.read()
                        last_pos = f.tell()
                    for line in chunk.splitlines():
                        if line and (not filter or filter.lower() in line.lower()):
                            yield f"data: {line}\n\n"
                db = SessionLocal()
                try:
                    ex = db.query(ResourceExecution).filter(
                        ResourceExecution.id == execution_id
                    ).first()
                    if ex and ex.status != "running":
                        yield "event: done\ndata: \n\n"
                        return
                finally:
                    db.close()
                await asyncio.sleep(0.5)
                waited += 0.5
            yield "event: done\ndata: timeout\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    result = read_filtered(log_path)
    return PlainTextResponse("".join(result) if result else "")


@app.get("/api/catastro/lookup")
async def catastro_lookup(lat: float = Query(..., description="Latitud WGS84"), lon: float = Query(..., description="Longitud WGS84")):
    """
    Dado un punto geográfico (lat, lon), devuelve los datos catastrales del inmueble
    en esa ubicación consultando el OVC de la Dirección General del Catastro vía SOAP.

    Paso 1: coordenadas → Referencia Catastral  (Consulta_RCCOOR SOAP)
    Paso 2: RC → datos del inmueble             (Consulta_DNPRC SOAP)
    """
    from zeep import Client, Settings
    from zeep.helpers import serialize_object
    from lxml import etree

    WSDL_COORD = "https://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/OVCCoordenadas.asmx?WSDL"
    WSDL_CALLEJERO = "https://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/OVCCallejero.asmx?WSDL"
    settings = Settings(strict=False, xml_huge_tree=True)

    # ── Paso 1: lat/lon → RC vía Consulta_RCCOOR ─────────────────────────────
    try:
        client_coord = Client(WSDL_COORD, settings=settings)
        raw = client_coord.service.Consulta_RCCOOR(
            SRS="EPSG:4326",
            Coordenada_X=str(lon),
            Coordenada_Y=str(lat),
        )
        # raw es un lxml Element con namespace http://www.catastro.meh.es/
        xml_str = etree.tostring(raw, encoding="unicode")
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml_str)
        ns = "http://www.catastro.meh.es/"
        cuerr = root.findtext(f"{{{ns}}}control/{{{ns}}}cuerr") or root.findtext(".//cuerr") or "0"
        if cuerr != "0":
            lerr = root.findtext(f".//{{{ns}}}lerr") or root.findtext(".//lerr")
            raise HTTPException(status_code=404, detail=lerr or "No se encontró parcela catastral en esas coordenadas")
        pc1 = (root.findtext(f".//{{{ns}}}pc1") or root.findtext(".//pc1") or "").strip()
        pc2 = (root.findtext(f".//{{{ns}}}pc2") or root.findtext(".//pc2") or "").strip()
        ldt = root.findtext(f".//{{{ns}}}ldt") or root.findtext(".//ldt") or ""
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Error consultando Catastro OVC (coordenadas): {exc}")

    if not pc1 or not pc2:
        raise HTTPException(status_code=404, detail="No se encontró referencia catastral para esas coordenadas")

    rc_parcela = pc1 + pc2

    def _safe_int(v):
        try:
            return int(v) if v is not None else None
        except (ValueError, TypeError):
            return None

    client_cal = Client(WSDL_CALLEJERO, settings=settings)

    # ── Paso 2: RC parcela → lista de fincas + datos de ubicación ────────────
    try:
        raw2 = client_cal.service.Consulta_DNPRC(Provincia="", Municipio="", RC=rc_parcela)
        xml2 = etree.tostring(raw2, encoding="unicode")
        root2 = ET.fromstring(xml2)
        ns = "http://www.catastro.meh.es/"

        # Extraer primera finca para obtener su RC completo (pc1+pc2+car+cc1+cc2)
        first_rcdnp = root2.find(f".//{{{ns}}}rcdnp")
        rc_finca = None
        municipio = provincia = direccion = None

        if first_rcdnp is not None:
            fpc1 = (first_rcdnp.findtext(f".//{{{ns}}}pc1") or "").strip()
            fpc2 = (first_rcdnp.findtext(f".//{{{ns}}}pc2") or "").strip()
            fcar = (first_rcdnp.findtext(f".//{{{ns}}}car") or "").strip()
            fcc1 = (first_rcdnp.findtext(f".//{{{ns}}}cc1") or "").strip()
            fcc2 = (first_rcdnp.findtext(f".//{{{ns}}}cc2") or "").strip()
            if fpc1 and fpc2 and fcar:
                rc_finca = fpc1 + fpc2 + fcar + fcc1 + fcc2

            dt2 = first_rcdnp.find(f".//{{{ns}}}dt")
            if dt2 is not None:
                municipio = dt2.findtext(f"{{{ns}}}nm")
                provincia = dt2.findtext(f"{{{ns}}}np")
                ldir2 = dt2.find(f".//{{{ns}}}dir")
                if ldir2 is not None:
                    tv = ldir2.findtext(f"{{{ns}}}tv") or ""
                    nv = ldir2.findtext(f"{{{ns}}}nv") or ""
                    pnp = ldir2.findtext(f"{{{ns}}}pnp") or ""
                    direccion = " ".join(filter(None, [tv, nv, pnp])).strip() or None

        unidades = len(root2.findall(f".//{{{ns}}}rcdnp"))
    except Exception:
        rc_finca = None
        municipio = provincia = direccion = None
        unidades = None

    direccion = direccion or ldt or None

    # ── Paso 3: RC finca → uso, superficie, año (debi) ────────────────────────
    uso = sup_suelo = sup_construida = plantas = año = None
    if rc_finca:
        try:
            raw3 = client_cal.service.Consulta_DNPRC(Provincia="", Municipio="", RC=rc_finca)
            xml3 = etree.tostring(raw3, encoding="unicode")
            root3 = ET.fromstring(xml3)
            ns = "http://www.catastro.meh.es/"
            debi = root3.find(f".//{{{ns}}}debi")
            if debi is not None:
                uso         = debi.findtext(f"{{{ns}}}luso")
                sup_suelo   = _safe_int(debi.findtext(f"{{{ns}}}sfc"))
                plantas     = _safe_int(debi.findtext(f"{{{ns}}}npt"))
                año         = _safe_int(debi.findtext(f"{{{ns}}}ant"))
            lcons = root3.find(f".//{{{ns}}}dfcons")
            if lcons is not None:
                sup_construida = _safe_int(lcons.findtext(f"{{{ns}}}stl"))
        except Exception:
            pass

    return {
        "rc_parcela":        rc_parcela,
        "rc_finca":          rc_finca,
        "municipio":         municipio,
        "provincia":         provincia,
        "direccion":         direccion,
        "unidades":          unidades,
        "uso":               uso,
        "sup_suelo_m2":      sup_suelo,
        "sup_construida_m2": sup_construida,
        "plantas":           plantas,
        "año_construccion":  año,
    }


def _face_code_to_nivel(code: str) -> int:
    """Infer administrative level from DIR3 code prefix."""
    if not code:
        return 0
    if code.startswith("E"):
        return 1   # AGE / Estatal
    if code.startswith("A"):
        return 2   # Autonómica
    if code.startswith("L03") or code.startswith("L04"):
        return 3   # Provincial (Diputaciones, Cabildos, Consejos)
    if code.startswith("L"):
        return 4   # Local (Ayuntamientos, entidades locales)
    return 0


def _get_latest_staging(db, name_pattern: str) -> str | None:
    """Return the staging_path of the most-recent completed execution for a resource."""
    res = (
        db.query(Resource)
        .filter(Resource.name.ilike(name_pattern))
        .first()
    )
    if not res:
        return None
    exec_ = (
        db.query(ResourceExecution)
        .filter(
            ResourceExecution.resource_id == res.id,
            ResourceExecution.status == "completed",
            ResourceExecution.staging_path.isnot(None),
        )
        .order_by(ResourceExecution.started_at.desc())
        .first()
    )
    return exec_.staging_path if exec_ else None


@app.get("/api/dir3/search")
async def dir3_search(
    q: str = Query(default=""),
    nivel: int = Query(default=0, description="adm_level_id (0=all, 1=AGE, 2=Autonómica, 3=Provincial, 4=Local)"),
    max_hier: int = Query(default=3, description="Max hierarchical_level for Junta DIR3 data"),
    limit: int = Query(default=60, le=200),
    prov: str = Query(default="", description="2-digit INE province code to filter L01/L03 codes"),
):
    """Search DIR3 units from Junta DIR3 staging AND FACE relations staging."""
    import json

    db = SessionLocal()
    try:
        dir3_path = _get_latest_staging(db, "%dir3%unidades%")
        face_path = _get_latest_staging(db, "%face%relaciones%")
    finally:
        db.close()

    q_lower = q.strip().lower()
    results = []
    seen_codes: set = set()

    # ── Source 1: Junta DIR3 ──────────────────────────────────────────────
    if dir3_path and os.path.exists(dir3_path):
        with open(dir3_path, "r", encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                if rec.get("state") != "V":
                    continue
                if nivel and int(rec.get("adm_level_id") or 0) != nivel:
                    continue
                if int(rec.get("hierarchical_level") or 99) > max_hier:
                    continue
                code = rec.get("id", "")
                if prov and not (code.startswith(f"L01{prov}") or code.startswith(f"L03{prov}")):
                    continue
                if q_lower and q_lower not in rec.get("name", "").lower():
                    continue
                if code in seen_codes:
                    continue
                seen_codes.add(code)
                results.append({
                    "id": code,
                    "name": rec.get("name"),
                    "adm_level_id": int(rec.get("adm_level_id") or 0),
                    "adm_level_name": rec.get("adm_level_name"),
                    "nif_cif": rec.get("nif_cif"),
                    "source": "dir3",
                })
                if len(results) >= limit:
                    break

    # ── Source 2: FACE relations (deduplicated by administration.code) ────
    if face_path and os.path.exists(face_path) and len(results) < limit:
        with open(face_path, "r", encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                adm = rec.get("administration") or {}
                code = adm.get("code", "")
                name = adm.get("name", "")
                if not code or not rec.get("active", True):
                    continue
                if code in seen_codes:
                    continue
                inferred_nivel = _face_code_to_nivel(code)
                if nivel and inferred_nivel != nivel:
                    continue
                if prov and not (code.startswith(f"L01{prov}") or code.startswith(f"L03{prov}")):
                    continue
                if q_lower and q_lower not in name.lower():
                    continue
                seen_codes.add(code)
                results.append({
                    "id": code,
                    "name": name,
                    "adm_level_id": inferred_nivel,
                    "adm_level_name": {1: "AGE", 2: "Autonómica", 3: "Provincial", 4: "Local"}.get(inferred_nivel, ""),
                    "nif_cif": None,
                    "source": "face",
                })
                if len(results) >= limit:
                    break

    if not dir3_path and not face_path:
        raise HTTPException(status_code=404, detail="No DIR3/FACE staging data found. Run DIR3 or FACE resource first.")

    return {"results": results, "total": len(results), "truncated": len(results) >= limit}


@app.get("/api/check-url")
async def check_url(url: str):
    """Verifica si una URL es accesible (HEAD). Usado para validar portal_url en publishers."""
    import asyncio, urllib.request, urllib.error
    def _head(u):
        req = urllib.request.Request(u, method="HEAD",
              headers={"User-Agent": "OpenDataManager/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=8) as r:
                return {"ok": r.status < 400, "status": r.status}
        except urllib.error.HTTPError as e:
            return {"ok": e.code < 400, "status": e.code}
        except urllib.error.URLError as e:
            return {"ok": False, "error": str(e.reason)[:80]}
        except Exception as e:
            return {"ok": False, "error": str(e)[:80]}
    return await asyncio.get_event_loop().run_in_executor(None, _head, url)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8040, reload=True)
