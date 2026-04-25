# WebTreeFetcher + ResourceCandidate — diseño

> Documento de referencia técnica autoritativo. Sustituye a cualquier diseño previo
> sobre apificación de portales web clásicos (Vision A `LegacyDataPortalFetcher`,
> Vision B `PortalFilesCataloguer`, Vision C "discover + child resources directos",
> y la propuesta intermedia file-granular del spec previo de la rama
> `feature/resource-candidate`).

## Problema

Apificar portales web clásicos (HTML con árbol de páginas y enlaces a XLSX/PDF)
detectando la **taxonomía implícita** en la estructura de URLs y generando un
`Resource` hijo por cada agrupación inferida — no por cada fichero, no por cada
"sección" plana, sino por cada patrón de agrupación detectado por el algoritmo.

Ejemplo motivador:

```
/transparencia/economica/2021/presupuesto.xlsx
/transparencia/economica/2022/presupuesto.xlsx
/transparencia/economica/2023/presupuesto.xlsx
/transparencia/economica/2024/presupuesto.xlsx
/transparencia/economica/2025/presupuesto.xlsx
```

→ Una única propuesta de agrupación: `Presupuesto económico anual` con dimensión
`year` y 5 URLs casadas. Al promoverla se crea **un solo** `Resource` hijo cuyos
registros llevan `year` como columna añadida.

## Lenguaje OpenDataManager

| Concepto | Mapeo |
|---|---|
| **Fetcher** (clase, en `fetchers_enum.py`) | `WebTreeFetcher` (NUEVO) — sustituye `LegacyDataPortalFetcher` y `PortalFilesCataloguer`. Dos modos: `discover` (recorre el árbol, no descarga, devuelve URLs hoja con sus segmentos) y `stream` (descarga URLs concretas y enriquece con columnas-dimensión). |
| **Resource crawler** (padre) | Resource normal con `fetcher = WebTreeFetcher`, params `{start_url, max_depth, allowed_extensions, ...}`. Su `schedule` puede dispararse desde la UI de scheduling existente — sin tratamiento especial. |
| **Servicio de inferencia** (NUEVO) | `app/services/grouping_inferer.py` — recibe la lista de URLs hoja del `discover()` y emite propuestas de agrupación. **No es un fetcher**: no es origen de datos, es post-procesado. |
| **`ResourceCandidate`** (entidad NUEVA) | Cada propuesta de agrupación. Persistente, con ciclo de vida explícito. Fields detallados abajo. |
| **`Discovering.vue`** (vista existente, refactorizada) | Cambia su fuente de datos: en vez de listar "secciones" del JSON-artifact, lista los `ResourceCandidate` del crawler seleccionado. Acciones: aprobar (`promote`), descartar (`discard`), fundir (`merge`), partir (`split`). |
| **Resource hijo** (resultado de promover) | Resource con `parent_resource_id = crawler.id`, `auto_generated = true`, `fetcher = WebTreeFetcher` modo `stream`, params `{matched_urls, dimensions_to_add}`. Produce un `Dataset` versionado igual que cualquier otro Resource. Se programa con la UI de scheduling existente. |

## Algoritmo de inferencia

`GroupingInferer` opera sobre la lista plana de URLs hoja descubiertas y
produce una lista de `GroupingProposal`.

### Reconocedores de dimensión (v1)

Aplicados en orden, cada uno marca un segmento del path como dimensión si casa:

1. **Año**: regex `^(19|20)\d{2}$` y valor en rango `[1990, current_year + 1]`.
2. **Mes**: `01..12` o nombres en español/inglés (`enero..diciembre`, `january..december`).
3. **Trimestre**: `T1..T4`, `Q1..Q4`, `1T..4T`.
4. **Fecha completa**: `YYYY-MM-DD`, `YYYY_MM`, `YYYYMMDD`.
5. **DIR3**: códigos válidos contra la tabla DIR3 (cuando esté integrada).
6. **Genérico**: segmento que varía con ≥ N hermanos manteniendo el resto del
   path constante. Dimensión sin tipar; el operador la nombra al promover.

### Construcción de propuestas

1. **Tokenización**: cada URL → lista de segmentos.
2. **Trie**: árbol de prefijos sobre los segmentos.
3. **Detección por nivel**: en cada nodo, si los hijos forman un conjunto de
   valores que un reconocedor identifica como dimensión Y los sub-árboles bajo
   cada valor son **isomorfos** (misma forma de path), emitir propuesta
   colapsando ese nivel.
4. **Apilamiento**: si el sub-árbol colapsado tiene a su vez una dimensión
   interna (ej. year + trimestre), apilar dimensiones. Máximo 2 dimensiones en v1.
5. **Residuos**: URLs no agrupadas → propuestas individuales sin dimensiones.

### Score de confianza (heurísticas)

- Misma extensión en todos los `matched_urls` → +
- Mismo nombre base de fichero bajo distintos valores de dimensión → ++
- Cardinalidad ≥ 3 valores → +
- Reconocedor tipado (year, month) > genérico → +

El score se persiste y se muestra en la UI para priorizar la revisión.

## Modelo `ResourceCandidate`

```
opendata.resource_candidate

id                   UUID PK
execution_id         UUID FK → resource_execution    -- ejecución del crawler que la descubrió
fetcher_id           UUID FK → fetcher               -- el WebTreeFetcher
crawler_resource_id  UUID FK → resource              -- el resource padre (denormalizado para queries)

-- estructura inferida
path_template        TEXT                            -- ej. /transparencia/economica/{year}/presupuesto.xlsx
dimensions           JSONB                           -- [{name, segment_index, kind, sample_values}]
matched_urls         JSONB                           -- lista de URLs que casan
file_types           JSONB                           -- distribución {xlsx: 5, pdf: 0}

-- propuesta
suggested_name       TEXT
suggested_fetcher_id UUID FK → fetcher (nullable)    -- fetcher de descarga sugerido
confidence           REAL                            -- score [0..1]

-- ciclo de vida
status               TEXT                            -- discovered | reviewed | promoted | discarded | merged | split
promoted_resource_id UUID FK → resource (nullable)   -- el hijo creado al promover
merged_into_id       UUID FK → resource_candidate (nullable)  -- si fue fundido
split_from_id        UUID FK → resource_candidate (nullable)  -- si nació de un split

-- metadata
detected_at          TIMESTAMP
reviewed_at          TIMESTAMP
reviewed_by          TEXT
deleted_at           TIMESTAMP                       -- soft-delete (patrón consistente del proyecto)
```

Índices: `(crawler_resource_id, status)`, `(execution_id)`, `(status, deleted_at)`.

### Ciclo de vida

```
discovered ──► reviewed ──► promoted
            └► discarded
            └► merged    (target en otro candidato vía merged_into_id)
            └► split     (origen de N candidatos hijos vía split_from_id)
```

## Flujo end-to-end

1. Operador crea un Resource crawler con `fetcher = Web Tree`, `crawl_mode = discover`.
2. Lo ejecuta desde la vista `Discovering.vue` (o vía schedule).
3. `FetcherManager` invoca `WebTreeFetcher.discover()` → lista de URLs hoja.
4. `FetcherManager` pasa la lista a `GroupingInferer.infer()` → `GroupingProposal[]`.
5. `FetcherManager` persiste cada propuesta como `ResourceCandidate` (status `discovered`).
6. La UI muestra los candidatos. El operador revisa, posiblemente funde/parte, y promueve.
7. Promover crea un Resource hijo (`auto_generated=true`, `parent_resource_id=crawler.id`)
   con `fetcher = Web Tree` modo `stream`, params `{matched_urls, dimensions_to_add}`.
8. El hijo se programa (o ejecuta manualmente) desde la UI de scheduling estándar.
9. Su ejecución descarga las URLs, añade las dimensiones como columnas, produce un
   Dataset versionado igual que cualquier otro Resource.

## Decisiones de diseño cerradas

### El fetcher no recibe `db_session`

`WebTreeFetcher.discover()` devuelve la lista de URLs hoja como output puro.
La persistencia de candidatos es responsabilidad del `FetcherManager` (orquestador),
no del fetcher. El fetcher es testeable sin BD.

### La descarga del hijo es estática

Un Resource hijo guarda `matched_urls` literales. Si el portal añade una URL nueva
para una dimensión existente (un `2026` cuando había `2021..2025`), se recoge en
la siguiente ejecución del crawler padre — que detectará un candidato actualizable
y se ofrecerá al operador refrescar el Resource hijo asociado. **No** se intenta
generar URLs sintéticas iterando rangos: demasiado frágil.

### Re-discover sobre candidatos ya promovidos

Cuando el crawler padre se re-ejecuta, `GroupingInferer` casa nuevas propuestas
contra `ResourceCandidate.status = promoted` por `path_template`:

- Si encuentra URLs nuevas para una propuesta ya promovida → marca el candidato
  como `needs_refresh` y notifica en la UI; el operador acepta y se actualiza
  `matched_urls` del Resource hijo correspondiente.
- Si la propuesta es enteramente nueva → nuevo `ResourceCandidate` en `discovered`.

### Promover usa el mismo fetcher en modo stream

El Resource hijo usa `WebTreeFetcher` con `crawl_mode = stream` — no requiere
fetchers específicos por formato. El parseo XLSX/PDF/CSV se delega a los
parseadores compartidos en `app/fetchers/file_parsers.py` (ya existentes).

## Ficheros nuevos

```
app/fetchers/web_tree_fetcher.py            -- fetcher con discover + stream
app/services/grouping_inferer.py            -- algoritmo de inferencia
alembic/versions/<rev>_add_resource_candidate.py
```

## Ficheros modificados

```
app/models.py                                -- añade ResourceCandidate
app/fetchers/fetchers_enum.py                -- añade WEB_TREE
app/manager/fetcher_manager.py               -- post-discover invoca GroupingInferer y persiste candidatos
app/graphql_api/queries.py                   -- queries de candidatos
app/graphql_api/mutations.py                 -- mutations promote/discard/merge/split
app/graphql_api/types.py                     -- tipos GraphQL
frontend/src/api/graphql.js                  -- operaciones de candidatos
frontend/src/views/Discovering.vue           -- refactor: candidatos en vez de secciones
frontend/src/views/Resources.vue             -- elimina botón discover ad-hoc
README.md                                    -- referencias Portal Documental → Web Tree
docs/resource_bundle_import.md               -- ejemplos con Web Tree
```

## Ficheros eliminados

```
app/fetchers/legacy_data_portal.py           -- absorbido por WebTreeFetcher
app/fetchers/portal_files_cataloguer.py      -- absorbido por WebTreeFetcher
frontend/src/views/DiscoverModal.vue         -- el flujo vive ahora en Discovering.vue
frontend/src/views/kkk.vue                   -- scratch olvidado
```

Y se retira código:

- `_discover_mode` runtime param en `fetcher_manager.py`
- `discover_artifact` / `discover_artifact_for_execution` queries
- `create_child_resources` mutation
- `discoverArtifact` field en `ResourceType` (si existe)
- `isDiscoverable()` función string-match en `Resources.vue`
