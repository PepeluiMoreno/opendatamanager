"""
Servidor principal FastAPI + Strawberry GraphQL.

Ejecutar con:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8040
"""
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from strawberry.fastapi import GraphQLRouter
from app.graphql.schema import schema
from app.database import SessionLocal
from app.models import Dataset, Resource
from app.services.scheduler_service import SchedulerService

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8040, reload=True)
