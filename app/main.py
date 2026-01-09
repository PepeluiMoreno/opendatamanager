"""
Servidor principal FastAPI + Strawberry GraphQL.

Ejecutar con:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8040
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter
from app.graphql.schema import schema

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8040,
        reload=True
    )
