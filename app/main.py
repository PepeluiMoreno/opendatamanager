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
from app.models import Artifact

# Crear aplicación FastAPI
app = FastAPI(
    title="OpenDataManager API",
    description="API GraphQL para gestión de fuentes de datos OpenData",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurar router GraphQL
graphql_app = GraphQLRouter(schema, graphiql=True)
app.include_router(graphql_app, prefix="/graphql")


@app.get("/")
def root():
    """Endpoint raíz con información de la API"""
    return {
        "name": "OpenDataManager API",
        "version": "1.0.0",
        "graphql_endpoint": "/graphql",
        "graphiql_ui": "/graphql (navegador)",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/api/artifacts/{artifact_id}/data.jsonl")
async def download_artifact_data(artifact_id: str):
    """Download artifact data file"""
    session = SessionLocal()
    try:
        artifact = session.query(Artifact).filter(Artifact.id == artifact_id).first()
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found")
        if not os.path.exists(artifact.data_path):
            raise HTTPException(status_code=404, detail="Data file not found")
        return FileResponse(artifact.data_path, media_type="application/x-ndjson")
    finally:
        session.close()


@app.get("/api/artifacts/{artifact_id}/schema.json")
async def download_artifact_schema(artifact_id: str):
    """Download artifact schema file"""
    session = SessionLocal()
    try:
        artifact = session.query(Artifact).filter(Artifact.id == artifact_id).first()
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found")

        artifact_dir = os.path.dirname(artifact.data_path)
        schema_path = f"{artifact_dir}/schema.json"

        if not os.path.exists(schema_path):
            raise HTTPException(status_code=404, detail="Schema file not found")

        return FileResponse(schema_path, media_type="application/json")
    finally:
        session.close()


@app.get("/api/artifacts/{artifact_id}/models.py")
async def download_artifact_models(artifact_id: str):
    """Download artifact models file"""
    session = SessionLocal()
    try:
        artifact = session.query(Artifact).filter(Artifact.id == artifact_id).first()
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found")

        artifact_dir = os.path.dirname(artifact.data_path)
        models_path = f"{artifact_dir}/models.py"

        if not os.path.exists(models_path):
            raise HTTPException(status_code=404, detail="Models file not found")

        return FileResponse(models_path, media_type="text/x-python")
    finally:
        session.close()


@app.get("/api/artifacts/{artifact_id}/metadata.json")
async def download_artifact_metadata(artifact_id: str):
    """Download artifact metadata file"""
    session = SessionLocal()
    try:
        artifact = session.query(Artifact).filter(Artifact.id == artifact_id).first()
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found")

        artifact_dir = os.path.dirname(artifact.data_path)
        metadata_path = f"{artifact_dir}/metadata.json"

        if not os.path.exists(metadata_path):
            raise HTTPException(status_code=404, detail="Metadata file not found")

        return FileResponse(metadata_path, media_type="application/json")
    finally:
        session.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8040,
        reload=True
    )
