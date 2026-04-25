Actúa como arquitecto senior de software especializado en pipelines de datos, scraping web y plataformas de open data.

Objetivo

Diseñar la extensión de OpenDataManager (ODM) para convertir portales web clásicos (HTML con enlaces a XLSX/PDF organizados en árbol) en datasets publicados en CKAN.

El objetivo final es:

Poblar CKAN correctamente
Exponer los datos vía su API REST
Usar ODM como motor de ingestión, normalización y publicación
Contexto técnico
Backend: Python
API: FastAPI
UI (solo administración): Vue 3
DB: PostgreSQL
Output: CKAN
Corrección conceptual clave (OBLIGATORIA)
WebTree NO es un Resource
WebTree es un tipo de Fetcher

El modelo debe respetar:

Fetcher = origen dinámico de datos (API, Web, Files, etc.)
Resource = unidad de dato descubierta (dataset potencial)
Principios de arquitectura
Separación estricta:
fetch
scrape
process
normalize
publish
Idempotencia total
Versionado por hash
Staging obligatorio
Sistema extensible (plugins/estrategias)
1. Arquitectura del pipeline
fetch → scrape → process → normalize → stage → publish

Define:

inputs/outputs de cada fase
contratos entre fases
gestión de errores y reintentos
2. Modelo de dominio en ODM

Define entidades correctamente separadas:

Fetchers
BaseFetcher
WebTreeFetcher (NUEVO)

Campos WebTreeFetcher:

root_url
allowed_domains
max_depth
include_patterns
exclude_patterns
Entidades de ingestión
RawPage
url
html
status
fetched_at
parent_url
DiscoveredResource
url
type (pdf/xlsx/html)
source_page
detected_at
Entidades de datos (staging)
Dataset
id
title
description
slug
status
source (fetcher_id)
Resource
id
dataset_id
url
format
hash
metadata
DatasetVersion
dataset_id
version
hash
created_at
Jobs
Job
type
status
started_at
finished_at
logs
3. Estados del pipeline

Estados obligatorios:

RAW → SCRAPED → PROCESSED → NORMALIZED → READY → PUBLISHED → ERROR

Define:

transición exacta
condiciones de paso
reintentos
4. WebTreeFetcher (capa fetch)

Responsabilidad:

crawling del portal
descubrir páginas y recursos

Debe:

soportar BFS o DFS
evitar duplicados
persistir progreso (crawl incremental)

Salida:

RawPage
DiscoveredResource
5. Sistema de scrapers

NO mezclar con fetcher.

Diseñar:

BaseScraper
GenericHTMLScraper
TablePageScraper
DocumentPageScraper

Debe soportar:

selección por reglas
configuración declarativa (CSS selectors)
fallback
6. Procesadores
XLSXProcessor (pandas)
PDFProcessor

Salida estándar:

schema
preview
metadata
7. Normalizador → CKAN

Módulo: ckan_mapper

Mapeo:

Dataset ODM → dataset CKAN
Resource ODM → resource CKAN
categorías → groups/tags

Reglas:

slug determinista
deduplicación
coherencia de naming
8. Publisher CKAN

Componente: CKANPublisher

Funciones:

upsert_dataset
upsert_resource

Requisitos:

idempotencia
detección de cambios por hash
uso API CKAN
9. Sistema de jobs

Tipos:

crawl_job
scrape_job
process_job
normalize_job
publish_job

Debe incluir:

colas
reintentos
logs estructurados
trazabilidad
10. API (FastAPI)

Endpoints:

POST /jobs/crawl
POST /jobs/publish
GET /datasets
GET /datasets/{id}
POST /datasets/{id}/approve
GET /logs
11. UI administración (Vue 3)

Módulos:

gestión de fetchers (WebTree)
ejecución de jobs
staging datasets
aprobación manual
errores
configuración scraping

NO incluir portal público.

12. Estructura del proyecto

backend/
fetchers/
scrapers/
processors/
normalizer/
publishers/
models/
jobs/
api/

frontend/
views/
components/
store/

13. Decisiones clave

Explicar:

por qué WebTree es fetcher y no resource
por qué staging es obligatorio
por qué scraping debe ser desacoplado
limitaciones con PDFs
cómo tratar HTML inconsistente
14. Plan por fases

Fase 1:

WebTreeFetcher + scraping básico + publish directo

Fase 2:

staging + estados

Fase 3:

normalización completa

Fase 4:

UI administración
Restricciones
NO escribir código
NO simplificar en exceso
diseñar para datos sucios y HTML inconsistente
priorizar robustez
Resultado esperado

Diseño técnico completo y coherente con OpenDataManager, donde WebTreeFetcher actúa como origen de datos y CKAN como destino final para “apificar” portales legacy.