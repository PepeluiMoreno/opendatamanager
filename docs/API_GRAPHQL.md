# API GraphQL de OpenDataManager

> **Nota:** GraphQL no usa Swagger/OpenAPI (eso es para REST). El "contrato" de
> una API GraphQL es su **propio esquema**, introspectable y autodescriptivo.
> Este documento es la referencia legible; el contrato máquina-legible es
> [`schema.graphql`](schema.graphql) (SDL), y la exploración interactiva está en
> **GraphiQL** (abre `/graphql` en el navegador).

## Endpoints

| Endpoint | Para qué |
|---|---|
| `POST /graphql` | API de **gestión**: fetchers, recursos, discovery. Sirve GraphiQL en navegador. |
| `POST /graphql/data` | API de **datos**: lectura de los datasets ya cargados (esquema dinámico por dataset). |

## Autenticación

Sesión por cookie:

```
POST /api/auth/login    { "username": "...", "password": "..." }
→ Set-Cookie: <sesión>   (el cuerpo incluye los `permisos` efectivos)
```

Las operaciones exigen permisos **RBAC** (ver cada operación). Para clientes
máquina (p. ej. suscriptores como `ckan-jerez`) usa una **cuenta de servicio** con
rol de mínimo privilegio. *(Pendiente: auth por token Bearer — ver backlog.)*

## Convenciones

- Campos en `camelCase`. Escalares especiales: `JSON`, `DateTime`.
- Errores: respuesta HTTP 200 con un array `errors` (estilo GraphQL).
- Identificadores: `String`/`ID` (UUID).

## El esquema (SDL)

Contrato completo en [`schema.graphql`](schema.graphql). Se regenera con:

```python
from app.graphql.schema import schema
print(schema.as_str())
```

---

## Fetchers

```graphql
query { fetchers { id name presets { id code } } }   # localizar fetcher + variantes
```
`fetchers: [FetcherType!]!` · `fetcher(id: String!): FetcherType`

## Recursos

| Operación | Firma | Permiso |
|---|---|---|
| Crear | `createResource(input: CreateResourceInput!): ResourceType!` | `recursos.crear` |
| Editar | `updateResource(id: String!, input: UpdateResourceInput!): ResourceType!` | `recursos.editar` |
| Clonar | `cloneResource(id: String!, name: String): ResourceType!` | `recursos.crear` |
| Borrar | `deleteResource(id: String!, hardDelete: Boolean! = false): Boolean!` | `recursos.borrar` |
| Ejecutar | `executeResource(id: String!, params: JSON): ExecutionResult!` | `ejecuciones.lanzar` |

```
input CreateResourceInput { name!  fetcherId!  params: [ResourceParamInput!]!
  description  active  publisher  publisherId  targetTable  schedule  presetId }
input ResourceParamInput { key!  value!  isExternal! }   # value es String: serializa a JSON lo compuesto
type ExecutionResult { success!  message!  resourceId  executionId  sampleData }
```

**Ejemplo — crear un recurso Web Tree (censo documental):**
```graphql
mutation Crear($input: CreateResourceInput!) {
  createResource(input: $input) { id name fetcher { name } preset { code } }
}
```
```json
{ "input": {
  "name": "Jerez — Portal de Transparencia (censo)",
  "fetcherId": "<id del fetcher Web Tree>",
  "presetId": "<id del preset 'Censo documental'>",
  "params": [ { "key": "root_url", "value": "https://transparencia.jerez.es/infopublica/economica", "isExternal": false } ]
} }
```

## Discovery (Web Tree)

El discovery se dispara **ejecutando el crawler** (recurso Web Tree padre) y es
**asíncrono**: produce candidatos que luego se revisan y promueven.

| Operación | Firma | Permiso |
|---|---|---|
| Disparar discovery | `executeResource(id, params)` | `ejecuciones.lanzar` |
| Listar candidatos | `resourceCandidates(crawlerResourceId: ID, executionId: ID, status: String): [ResourceCandidateType!]!` | lectura |
| Promover | `promoteCandidate(id: ID!, input: PromoteCandidateInput!): ResourceType!` | `recursos.crear` |
| Descartar | `discardCandidate(id: ID!, reviewer: String): ResourceCandidateType!` | `recursos.crear` |
| Fusionar | `mergeCandidates(sourceIds: [ID!]!, targetId: ID!): ResourceCandidateType!` | `recursos.crear` |
| Dividir | `splitCandidate(id: ID!, groups: JSON!): [ResourceCandidateType!]!` | `recursos.crear` |

```
input PromoteCandidateInput { name!  targetTable!  schedule  enableLoad=false
  loadMode="upsert"  variant }     # variant = code del preset (la variante)
type ResourceCandidateType { id  crawlerResourceId  pathTemplate  dimensions
  matchedUrls  fileTypes  suggestedName  confidence  status  promotedResourceId  … }
```

**Flujo completo (el que pilota `ckan-jerez`):**
```
createResource(crawler)            # define el árbol a recorrer
   → executeResource(crawler)      # dispara el discovery (asíncrono)
   → resourceCandidates(crawlerResourceId)   # revisa lo descubierto
   → promoteCandidate(id, { variant })       # por candidato, elige variante
```

### Variantes del fetcher Web Tree (presets)

| `code` (variant) | `extract_mode` | Qué hace |
|---|---|---|
| `Censo documental` | censo | registra cada hoja (sección, url, nombre, formato) sin extraer |
| `Extracción de datos` | datos | parsea ficheros tabulares (XLSX/CSV/PDF-tabla) a filas |
| `Extracción con receta` | receta | captura magnitudes concretas por receta declarativa |

## Manifiestos (import / export / plantilla)

Un **manifiesto** es un JSON declarativo (publisher + recursos por `fetcher` y
`preset`, ambos por *código*) para aprovisionar recursos de forma idempotente.

| Operación | Firma | Permiso |
|---|---|---|
| Importar | `mutation { importManifest(manifest: JSON) }` → `{ ok, created, updated, skipped, conflicts, errors }` | `recursos.crear` |
| Exportar | `query { resourceManifest(id: String!) }` → manifiesto del recurso | lectura |
| Plantilla | `query { manifestTemplate(fetcherCode: String!, presetCode: String) }` → manifiesto-esqueleto | lectura |

- **Idempotente:** publisher por `acronimo`, recurso por `(publisher, name)`; reimportar actualiza, no duplica.
- **Seguro:** referencia fetcher/preset por *código*; prohíbe `id`/`fetcher_id`/`class_path`.
- **Plantilla:** `manifestTemplate` arma el esqueleto desde el preset (sus params
  como punto de partida, sin los `locked_params`) con un bloque `_plantilla` de
  ayuda que el import ignora; `resourceManifest` exporta un recurso real como
  plantilla por ejemplo. Detalle en [`manifiestos.md`](manifiestos.md).

## Permisos (RBAC)

`recursos.crear` · `recursos.editar` · `recursos.borrar` · `ejecuciones.lanzar` ·
`ejecuciones.parar` · `fetchers.gestionar` · `settings.gestionar`.

Una cuenta de servicio **suscriptora** (define + descubre + promueve) necesita
típicamente: `recursos.crear`, `recursos.editar`, `ejecuciones.lanzar` y lectura.

## Consumo de datos

Los datasets cargados se leen por `POST /graphql/data` (esquema dinámico generado
por dataset). Esa cara es la que consumen los portales y cuadros de mando.
