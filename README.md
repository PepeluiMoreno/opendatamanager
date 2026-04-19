# OpenDataManager

**OpenDataManager (ODMGR)** es un backend metadata-driven para la ingesta, normalización y distribución de fuentes de datos abiertos heterogéneas. Expone una API GraphQL como interfaz de administración y orquesta un pipeline ETL completo con versionado semántico de datasets y notificación push a aplicaciones suscritas.

## Arquitectura general

El sistema se organiza en tres capas:

**1. Capa de metadatos (`opendata` schema)**
Toda la configuración del sistema reside en base de datos, no en ficheros de configuración. Cada fuente de datos (`Resource`) referencia un tipo de conector (`Fetcher`) identificado por su `class_path` y un conjunto de parámetros clave-valor (`ResourceParam`). Esto permite añadir, modificar o deshabilitar recursos en caliente sin redespliegue.

**2. Pipeline ETL**
La ejecución de un `Resource` atraviesa cuatro fases secuenciales:

- **Extract** — el `Fetcher` correspondiente descarga los datos de la fuente (REST, SOAP, CSV, XBRL, PDF, script externo, etc.) y los entrega como stream de registros.
- **Stage** — los registros se escriben en `/data/staging/{resource_id}/{execution_id}.jsonl` como punto de control auditado.
- **Load** — `DataLoader` lee el staging, ejecuta `normalize()` y hace upsert en `core.{target_table}`. El modo de carga (`replace` / `upsert`) es configurable por recurso.
- **Notify** — `ApplicationNotifier` despacha webhooks HMAC-signed a todas las aplicaciones suscritas al recurso. El payload varía según el `consumption_mode` de cada aplicación:
  - `webhook` — payload completo con metadatos del dataset y URL de descarga del JSONL.
  - `graphql` — aviso ligero; la aplicación consulta `/graphql/data` para obtener exactamente los campos que necesita.
  - `both` — recibe ambos: payload completo y referencia GraphQL.

**3. Capa de almacenamiento**
- **Staging**: filesystem temporal (JSONL), uno por ejecución.
- **Core schema**: tablas PostgreSQL normalizadas, listas para consumo analítico.

El webhook actúa de *trigger* event-driven; sin él, las aplicaciones consumidoras deberían implementar polling o lanzar su ETL a ciegas por cron. Como referencia, **GSH** consume ODMGR vía red Docker `traefik_public`: recibe el webhook al completarse una ejecución y consulta `/graphql/data` para ejecutar su propio ETL.

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Backend | FastAPI + Strawberry (GraphQL) |
| Frontend | Vue 3 + Vite |
| Base de datos | PostgreSQL (schemas `opendata` / `core`) |
| Migraciones | Alembic |
| Contenedores | Docker Compose (multi-env overlay) |
| Proxy / TLS | Traefik + nginx |

---

## Arquitectura de capas

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
│  │  - Fetcher, FetcherParams                            │  │
│  │  - Application, ResourceSubscription                 │  │
│  │  - ResourceExecution, ApplicationNotification        │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                   Storage Layer                             │
│  ┌─────────────────┐  ┌──────────────────────────────────┐ │
│  │ Staging (JSONL) │  │  core schema (datos normalizados) │ │
│  │ por ejecución   │  │  tablas listas para consumo       │ │
│  └─────────────────┘  └──────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Componentes principales

**Metadata Layer (`opendata` schema)**:
- **Fetcher** — registro de tipos de conector disponibles con su `class_path` para carga dinámica.
- **FetcherParams** — definición de parámetros requeridos/opcionales por tipo de fetcher.
- **Resource** — fuente de datos configurada: fetcher asignado, publisher, tabla destino, modo de carga.
- **ResourceParam** — parámetros clave-valor por resource (url, credenciales, rangos, etc.).
- **ResourceExecution** — audit trail de cada ejecución: estado, registros procesados, ruta de staging.
- **ResourceSubscription** — relación M:N entre Resources y Applications.
- **Application** — aplicación suscriptora con su webhook URL, secret HMAC y `consumption_mode`.
- **ApplicationNotification** — log de notificaciones emitidas con payload y código de respuesta HTTP.

**Processing Layer**:
- **FetcherManager** — orquestador del pipeline; instancia el fetcher correcto via `FetcherFactory` y coordina las cuatro fases.
- **DataLoader** — lee el staging JSONL y ejecuta el upsert hacia `core.{target_table}`.
- **ApplicationNotifier** — despacha webhooks HMAC-signed con reintentos configurables.

### Pipeline de ejecución

```
1. EXTRACT
   Resource → FetcherFactory → BaseFetcher.stream() → chunks de registros
   ↓
2. STAGE
   /data/staging/{resource_id}/{execution_id}.jsonl
   ↓
3. LOAD
   DataLoader → normalize() → upsert → core.{target_table}
   ↓
4. NOTIFY
   ApplicationNotifier → HMAC-signed POST → apps suscritas
   Payload según consumption_mode: JSONL URL | ping GraphQL | ambos
```

---

## Despliegue con Docker

Hay tres entornos: desarrollo local (`optiplex-790`), staging (`vps2.europalaica.org`) y producción (`vps1.europalaica.org`).

### Servicios por entorno

| Servicio | Dev | Staging/Prod |
|---|---|---|
| `app` (FastAPI + GraphQL) | bind mount + `--reload` | imagen construida |
| `frontend` (Vue 3) | Vite dev server, hot reload | build estático |
| `db` (PostgreSQL) | puerto expuesto al host | solo red interna |
| `nginx` | deshabilitado | proxy inverso + entrada Traefik |

### Red Docker

Todos los entornos se unen a la red externa `traefik_public`. La API (`odmgr_app`) es accesible desde otros proyectos Docker a través de esa red sin exponer puertos al host en staging/prod.

Para que un proyecto externo consuma la API basta con que se una a `traefik_public` y use `http://odmgr_app:8000/graphql` como endpoint.

### Archivos Compose

| Archivo | Uso |
|---|---|
| `docker-compose.yml` | Base común: servicios, volumes, red `traefik_public` |
| `docker-compose.dev.yml` | Overlay dev: bind mounts, puertos al host, Vite |
| `docker-compose.staging.yml` | Overlay staging: nginx + labels Traefik |
| `docker-compose.prod.yml` | Overlay producción: subdominio de prod |

### Variables de entorno

Copia `.env.example` como base. El archivo `.env` se carga automáticamente en desarrollo.

| Variable | Descripción |
|---|---|
| `APP_PREFIX` | Prefijo para nombres de contenedores (`odmgr`) |
| `FRONTEND_PORT` | Puerto del frontend Vite en dev (`5173`) |
| `POSTGRES_PORT` | Puerto externo de PostgreSQL (solo dev, `55432`) |
| `POSTGRES_USER` | Usuario de la base de datos |
| `POSTGRES_PASSWORD` | Contraseña de la base de datos |
| `POSTGRES_DB` | Nombre de la base de datos |
| `DATABASE_URL` | URL completa de conexión SQLAlchemy |

### Desarrollo

```sh
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d
```

Endpoints disponibles:

- `http://optiplex-790:5173` — Frontend Vue 3 (Vite, hot reload)
- `http://optiplex-790:5173/graphql` — GraphiQL UI (proxiado por Vite)
- `http://optiplex-790:5173/docs` — Swagger UI
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
# Sin borrar datos
docker compose -f docker-compose.yml -f docker-compose.dev.yml down

# Eliminando volumen de datos (destructivo)
docker compose -f docker-compose.yml -f docker-compose.dev.yml down -v
```

### Bootstrap de base de datos

La inicialización del schema no se ejecuta automáticamente al arrancar el contenedor. Se lanza manualmente:

```sh
bash scripts/db-bootstrap.sh
```

---

## API GraphQL — ejemplos

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

### Crear recurso

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

### Consultar ejecuciones

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

---

## Añadir un nuevo tipo de Fetcher

1. Crear clase heredando de `BaseFetcher` en `app/fetchers/`:

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

2. Registrar en BD (o vía migración Alembic):

```sql
INSERT INTO opendata.fetcher (id, code, class_path, description)
VALUES (
  gen_random_uuid(),
  'SOAP',
  'app.fetchers.soap.SOAPFetcher',
  'Cliente SOAP para web services'
);
```

`FetcherFactory` carga la clase dinámicamente por `class_path`; no requiere modificar código fuera del módulo del fetcher.

---

## Estructura del proyecto

```
opendatamanager/
├── app/
│   ├── database.py              # Configuración SQLAlchemy
│   ├── models.py                # Modelos ORM (opendata schema)
│   ├── core.py                  # Función upsert genérica
│   ├── fetchers/
│   │   ├── base.py              # BaseFetcher abstracto
│   │   ├── factory.py           # Carga dinámica por class_path
│   │   ├── registry.py          # Mapa code → metadata de fetchers
│   │   └── *.py                 # Implementaciones (rest, csv, xbrl, pdf_table…)
│   ├── manager/
│   │   └── fetcher_manager.py   # Orquestador del pipeline ETL
│   ├── graphql_api/
│   │   ├── schema.py            # Schema Strawberry
│   │   ├── types.py             # Tipos GraphQL
│   │   ├── queries.py
│   │   └── mutations.py
│   └── main.py                  # Servidor FastAPI
├── alembic/                     # Migraciones y seeds
├── scripts/
│   ├── db-bootstrap.sh          # Inicialización del schema
│   └── refresh_cores.py         # Ejecución batch de recursos
├── requirements.txt
└── README.md
```
