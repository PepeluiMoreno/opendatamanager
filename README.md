# OpenDataManager

Backend metadata-driven para gestión de recursos de datos OpenData con ETL automatizado y sistema de suscripciones.

## 🎯 Objetivos

1. **Gestionar recursos de datos** de portales oficiales mediante metadatos en BD
2. **Generar API GraphQL** automática para administración del sistema
3. **Refrescar core.models** de aplicaciones suscritas automáticamente
4. **Orquestar ETL completo**: Extract (fetchers) → Stage (filesystem) → Load (core schema) → Notify (webhooks)

## 🏗️ Arquitectura

### Arquitectura de Tres Capas

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Vue 3)                        │
│                   GraphQL API Client                        │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│              Backend (FastAPI + Strawberry)                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  opendata schema (metadata)                          │  │
│  │  - Resource, ResourceParam                           │  │
│  │  - FetcherType, TypeFetcherParams                    │  │
│  │  - Application, ResourceSubscription                 │  │
│  │  - ResourceExecution, ApplicationNotification        │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                   Storage Layer                             │
│  ┌─────────────────┐  ┌──────────────────────────────────┐ │
│  │ Staging (files) │  │  core schema (processed data)    │ │
│  │ - JSONL format  │  │  - Normalized tables             │ │
│  │ - Temporal      │  │  - Ready for consumption         │ │
│  └─────────────────┘  └──────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Componentes principales

**Metadata Layer (opendata schema)**:
- **FetcherType**: Tipos de fetchers disponibles (REST, SOAP, CSV, etc.) con su `class_path`
- **TypeFetcherParams**: Definición de parámetros requeridos/opcionales para cada FetcherType
- **Resource**: Recursos de datos configurados con parámetros
- **ResourceParam**: Parámetros key-value para cada Resource
- **ResourceExecution**: Tracking de cada ejecución de fetch (audit trail)
- **ResourceSubscription**: Relación M:N entre Resources y Applications
- **Application**: Aplicaciones suscritas que reciben actualizaciones automáticas
- **ApplicationNotification**: Log de notificaciones enviadas

**Processing Layer**:
- **API GraphQL**: Interfaz para gestionar y consultar todo el sistema
- **FetcherManager**: Orquestador que ejecuta fetchers
- **DataLoader**: Carga datos desde staging → core schema
- **ApplicationNotifier**: Notifica aplicaciones suscritas vía webhooks y genera modelos

**Storage Layer**:
- **Staging**: Filesystem temporal para raw data (JSONL)
- **Core Schema**: PostgreSQL schema con datos procesados y normalizados

### Pipeline de ejecución completo

```
1. EXTRACT
   Resource → FetcherFactory → BaseFetcher → fetch() → parse()
   ↓
2. STAGE
   Write to /data/staging/{resource_id}/{execution_id}.jsonl
   ↓
3. LOAD
   DataLoader reads JSONL → normalize() → upsert to core.{table}
   ↓
4. NOTIFY
   ApplicationNotifier:
   - Generate/update SQLAlchemy models for subscribed apps
   - Send HMAC-signed webhooks to notify data updates
```

## 🚀 Instalación

1. Clonar repositorio
2. Crear entorno virtual:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

3. Instalar dependencias:
```powershell
pip install -r requirements.txt
```

4. Configurar `.env`:
```env
DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/db?sslmode=require
API_HOST=localhost
API_PORT=8040
API_URL=http://localhost:8040/graphql
```

5. Ejecutar migraciones:
```powershell
python -m alembic upgrade head
```

## 🎮 Uso

### Iniciar servidor GraphQL

```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8040
```

Acceder a:
- **GraphQL API**: http://localhost:8040/graphql
- **GraphiQL UI**: http://localhost:8040/graphql (navegador)
- **Docs**: http://localhost:8040/docs

### Ejecutar fetchers manualmente

```powershell
# Ejecutar todos los sources activos
python scripts\refresh_cores.py

# Refrescar modelos de aplicaciones suscritas
python scripts\refresh_app_models.py
```

## 📝 Ejemplos GraphQL

### Listar recursos activos

```graphql
query {
  resources(activeOnly: true) {
    id
    name
    publisher
    targetTable
    fetcherType {
      code
      classPath
      paramsDef {
        paramName
        required
        dataType
      }
    }
    params {
      key
      value
    }
  }
}
```

### Crear nuevo recurso

```graphql
mutation {
  createResource(input: {
    name: "INE Población"
    publisher: "INE"
    targetTable: "poblacion"
    fetcherTypeId: "<uuid-del-rest-fetcher>"
    params: [
      {key: "url", value: "https://api.ine.es/poblacion"}
      {key: "auth_token", value: "your-token-here"}
    ]
    active: true
  }) {
    id
    name
    targetTable
  }
}
```

### Ejecutar recurso

```graphql
mutation {
  executeResource(id: "<resource-uuid>") {
    success
    message
    executionId
  }
}
```

### Consultar ejecuciones de un recurso

```graphql
query {
  resourceExecutions(resourceId: "<resource-uuid>") {
    id
    status
    totalRecords
    recordsLoaded
    startedAt
    completedAt
    stagingPath
  }
}
```

## 🔧 Agregar nuevo tipo de Fetcher

1. Crear clase heredando de `BaseFetcher`:

```python
# app/fetchers/soap.py
from app.fetchers.base import BaseFetcher, RawData, ParsedData, DomainData
from zeep import Client

class SOAPFetcher(BaseFetcher):
    def fetch(self) -> RawData:
        client = Client(self.params['wsdl'])
        return client.service.getData()

    def parse(self, raw: RawData) -> ParsedData:
        return raw

    def normalize(self, parsed: ParsedData) -> DomainData:
        return parsed
```

2. Registrar en BD:

```sql
INSERT INTO opendata.fetcher_type (id, code, class_path, description)
VALUES (
  gen_random_uuid(),
  'soap',
  'app.fetchers.soap.SOAPFetcher',
  'Cliente SOAP para web services'
);
```

¡Ya está! El sistema lo cargará dinámicamente.

## 📚 Estructura del Proyecto

```
opendatamanager/
├── app/
│   ├── database.py          # Configuración SQLAlchemy
│   ├── models.py             # Modelos de BD
│   ├── core.py               # Función upsert genérica
│   ├── fetchers/
│   │   ├── base.py           # BaseFetcher abstracto
│   │   ├── rest.py           # RESTFetcher
│   │   └── factory.py        # Factory dinámico
│   ├── manager/
│   │   └── fetcher_manager.py # Orquestador
│   ├── graphql/
│   │   ├── schema.py         # Schema Strawberry
│   │   ├── types.py          # Tipos GraphQL
│   │   ├── queries.py        # Queries
│   │   └── mutations.py      # Mutations
│   ├── refresh/
│   │   └── model_generator.py # Generador de modelos
│   └── main.py               # Servidor FastAPI
├── scripts/
│   ├── refresh_cores.py      # Ejecutar todos los sources
│   └── refresh_app_models.py # Refrescar apps suscritas
├── alembic/                  # Migraciones
├── requirements.txt
└── README.md
```
