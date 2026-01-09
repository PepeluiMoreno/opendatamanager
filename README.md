# OpenDataManager

Backend metadata-driven para gestión de fuentes de datos OpenData.

## 🎯 Objetivos

1. **Registrar fuentes de datos** de portales oficiales mediante metadatos en BD
2. **Generar API GraphQL** automática desde esas fuentes
3. **Refrescar core.models** de aplicaciones suscritas automáticamente

## 🏗️ Arquitectura

### Componentes principales

- **FetcherType**: Tipos de fetchers disponibles (REST, SOAP, CSV, etc.) con su `class_path`
- **Source**: Fuentes de datos configuradas con parámetros
- **SourceParam**: Parámetros key-value para cada Source
- **Application**: Aplicaciones suscritas que reciben actualizaciones automáticas
- **API GraphQL**: Interfaz para gestionar y consultar todo el sistema
- **FetcherManager**: Orquestador que ejecuta fetchers y actualiza datos

### Pipeline de ejecución

```
Source → FetcherFactory → BaseFetcher → fetch() → parse() → normalize() → upsert()
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

### Listar fuentes activas

```graphql
query {
  sources(activeOnly: true) {
    id
    name
    project
    fetcherType {
      code
      classPath
    }
    params {
      key
      value
    }
  }
}
```

### Crear nueva fuente

```graphql
mutation {
  createSource(input: {
    name: "INE Población"
    project: "demografia"
    fetcherTypeId: "<uuid-del-rest-fetcher>"
    params: [
      {key: "url", value: "https://api.ine.es/poblacion"}
    ]
    active: true
  }) {
    id
    name
  }
}
```

### Ejecutar fuente

```graphql
mutation {
  executeSource(id: "<source-uuid>") {
    success
    message
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
