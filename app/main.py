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

# Crear aplicación FastAPI
app = FastAPI(
    title="OpenDataManager API",
    description="API GraphQL para gestión de fuentes de datos OpenData",
    version="1.0.0"
)

scheduler_service = SchedulerService()

@app.on_event("startup")
async def startup_event():
    scheduler_service.start()
    scheduler_service.add_resource_jobs()

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

# Configurar router GraphQL
graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")


@app.get("/")
def root():
    return {
        "name": "OpenDataManager API",
        "version": "1.0.0",
        "graphql_endpoint": "/graphql",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


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
    """Returns container/host hardware info for the frontend to compute setting limits.
    Inside Docker, psutil reads cgroup limits — i.e. the memory actually allocated to this container.
    """
    import psutil
    vm = psutil.virtual_memory()
    cpu_logical = psutil.cpu_count(logical=True)
    cpu_physical = psutil.cpu_count(logical=False) or cpu_logical

    # Attempt to read Docker cgroup memory limit (more precise than vm.total inside containers)
    cgroup_limit_mb = None
    for path in ("/sys/fs/cgroup/memory/memory.limit_in_bytes",   # cgroup v1
                 "/sys/fs/cgroup/memory.max"):                     # cgroup v2
        try:
            with open(path) as f:
                val = f.read().strip()
            if val not in ("max", ""):
                limit_bytes = int(val)
                if limit_bytes < 2 ** 62:  # ignore "unlimited" sentinel
                    cgroup_limit_mb = round(limit_bytes / 1024 / 1024)
                    break
        except Exception:
            pass

    ram_total_mb = cgroup_limit_mb if cgroup_limit_mb else round(vm.total / 1024 / 1024)

    return {
        "ram_total_mb": ram_total_mb,
        "ram_available_mb": round(vm.available / 1024 / 1024),
        "ram_total_gb": round(ram_total_mb / 1024, 1),
        "cpu_logical": cpu_logical,
        "cpu_physical": cpu_physical,
        "source": "cgroup" if cgroup_limit_mb else "host",
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

    return {
        "total_threads": len(threads),
        "worker_threads": len(worker_threads),
        "running_executions": running,
        "threads": thread_list,
    }


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
            last_pos = 0
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8040, reload=True)
