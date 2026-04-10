# OpenDataManager

**OpenDataManager** es un **gestor automatizado de fuentes de datos abiertos**.

Imagina que trabajas en una organización y necesitas datos de varios sitios web del gobierno: subvenciones del Ministerio de Hacienda, catastro de la Junta de Andalucía, estadísticas del INE... Cada uno tiene su propia API, su propio formato, su propia forma de paginarse. Mantener todo eso a mano es un infierno.

Esta aplicación resuelve exactamente eso. Funciona en tres capas:

**1. Configuración de fuentes ("Resources")**
Defines de dónde quieres sacar datos: una URL de API REST, un portal CKAN, un feed RSS, un fichero CSV... Le dices cómo conectarse (qué parámetros usar, qué credenciales si las hay) y qué tipo de "conector" (fetcher) usar para cada tipo de fuente.

**2. Pipeline de extracción automática**
Cuando ejecutas un recurso, la app hace todo el trabajo sucio:
- **Extrae** los datos de la fuente
- **Normaliza** el formato (convierte todo a JSON estructurado)
- **Versiona** el resultado — si los datos cambian respecto a la vez anterior, crea una nueva versión (`v1.0.0`, `v1.1.0`, `v2.0.0`...) según si cambiaron los registros, la estructura, o ambas cosas
- **Guarda** el paquete de datos con su esquema, sus modelos Python generados automáticamente y sus metadatos

**3. Distribución a aplicaciones suscritas**
Otros proyectos pueden suscribirse a cualquier fuente. Cuando hay datos nuevos, ODMGR dispara automáticamente un **webhook** hacia cada aplicación suscrita, avisando de que hay una nueva versión disponible. A partir de ahí, la aplicación puede obtener los datos de dos formas según su `consumption_mode`:

- **`webhook`** — el propio webhook lleva el payload completo: metadatos del dataset y URL de descarga directa del fichero JSONL. La app descarga el fichero y ejecuta su ETL.
- **`graphql`** — el webhook es un aviso ligero ("hay datos nuevos en el recurso X"). La app consulta entonces `/graphql/data` para obtener exactamente lo que necesita.
- **`both`** — recibe ambas cosas: payload completo + referencia GraphQL.

El webhook y la API GraphQL **no son excluyentes**: el webhook actúa de *trigger* y GraphQL es el *transporte de datos*. Sin webhook, la app consumidora tendría que hacer polling ("¿hay algo nuevo?") o lanzar su ETL a ciegas por cron.

Por ejemplo, **GSH** es una aplicación que consume datos de ODMGR vía red Docker: recibe el webhook cuando hay una ejecución completada y ejecuta su ETL consultando `/graphql/data`.

En resumen: es un **hub centralizado de datos abiertos** que conecta fuentes heterogéneas, estandariza lo que sacan, lleva control de versiones como si fuera un git de datos, y avisa a quien lo necesite cuando hay novedades.

---

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
│  │  - Fetcher, FetcherParams                    │  │
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
- **Fetcher**: Tipos de fetchers disponibles (REST, SOAP, CSV, etc.) con su `class_path`
- **FetcherParams**: Definición de parámetros requeridos/opcionales para cada Fetcher
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
- **ApplicationNotifier**: Notifica aplicaciones suscritas vía webhooks (HMAC-signed)

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
   - Send HMAC-signed webhooks to subscribed apps
   - Payload varía según consumption_mode: JSONL URL (webhook), ping ligero (graphql), o ambos (both)
```

## 🚀 Despliegue con Docker

La aplicación corre en contenedores. Hay tres entornos: desarrollo local (`optiplex-790`), staging (`vps2.europalaica.org`) y producción (`vps1.europalaica.org`).

### Servicios por entorno

| Servicio | Dev | Staging/Prod |
|---|---|---|
| `app` (FastAPI + GraphQL) | bind mount + `--reload` | imagen construida |
| `frontend` (Vue 3) | Vite dev server, hot reload | build estático |
| `db` (PostgreSQL) | puerto expuesto al host | solo interno |
| `nginx` | no arranca | proxy + entrada Traefik |

### Red Docker

Todos los entornos comparten la red externa `traefik_public`. La API (`odmgr_app`) es accesible desde otros proyectos Docker a través de esa red — no se expone ningún puerto al host en staging/prod.

Para que otro proyecto consuma la API, basta con que se una a `traefik_public` y use `http://odmgr_app:8000/graphql` como URL.

### Archivos Compose

| Archivo | Uso |
|---|---|
| `docker-compose.yml` | Base común: servicios, red `traefik_public` |
| `docker-compose.dev.yml` | Overlay dev: bind mounts, puertos al host, frontend Vite |
| `docker-compose.staging.yml` | Overlay staging: añade nginx con labels Traefik |
| `docker-compose.prod.yml` | Overlay producción: igual con subdominio de prod |

### Variables de entorno

Copia `.env.example` como base. El archivo `.env` es cargado automáticamente en desarrollo.

| Variable | Descripción |
|---|---|
| `APP_PREFIX` | Prefijo para nombres de contenedores (`odmgr`) |
| `FRONTEND_PORT` | Puerto del frontend Vite en dev (`5173`) |
| `POSTGRES_PORT` | Puerto externo de PostgreSQL (solo dev, `55432`) |
| `POSTGRES_USER` | Usuario de la base de datos |
| `POSTGRES_PASSWORD` | Contraseña de la base de datos |
| `POSTGRES_DB` | Nombre de la base de datos |
| `DATABASE_URL` | URL completa de conexión (usada por la app Python) |

### Desarrollo (optiplex-790)

```sh
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d
```

Accesible en:
- `http://optiplex-790:5173` — Frontend (Vite dev server, hot reload)
- `http://optiplex-790:5173/graphql` — GraphiQL UI (proxiado por Vite)
- `http://optiplex-790:55432` — PostgreSQL directo

### Staging

```sh
docker compose --env-file .env.staging -f docker-compose.yml -f docker-compose.staging.yml up -d
```

### Producción

```sh
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Parar servicios

```sh
# Bajar sin borrar datos
docker compose -f docker-compose.yml -f docker-compose.dev.yml down

# Bajar y eliminar volumen de datos (destructivo)
docker compose -f docker-compose.yml -f docker-compose.dev.yml down -v
```

### Bootstrap de base de datos

La inicialización no ocurre automáticamente al arrancar. Se ejecuta manualmente:

```sh
bash scripts/db-bootstrap.sh
```

## 🎮 Uso

Endpoints disponibles en desarrollo:

- `http://optiplex-790:5173` — Frontend Vue 3
- `http://optiplex-790:5173/graphql` — GraphiQL UI
- `http://optiplex-790:5173/docs` — Swagger UI (proxiado por Vite)

En staging/prod, Traefik enruta el subdominio configurado hacia nginx, que sirve el frontend y hace proxy de `/graphql` hacia `app`.

## 📝 Ejemplos GraphQL

### Listar recursos activos

```graphql
query {
  resources(activeOnly: true) {
    id
    name
    publisher
    targetTable
    Fetcher {
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
    FetcherId: "<uuid-del-rest-fetcher>"
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
INSERT INTO opendata.fetcher (id, code, class_path, description)
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
│   ├── graphql_api/
│   │   ├── schema.py         # Schema Strawberry
│   │   ├── types.py          # Tipos GraphQL
│   │   ├── queries.py        # Queries
│   │   └── mutations.py      # Mutations
│   ├── refresh/
│   │   └── model_generator.py # Generador de modelos
│   └── main.py               # Servidor FastAPI
├── scripts/
│   ├── refresh_cores.py      # Ejecutar todos los  resources
│   └── refresh_app_models.py # Refrescar apps suscritas
├── alembic/                  # Migraciones
├── requirements.txt
└── README.md
```
