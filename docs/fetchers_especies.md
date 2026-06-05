# Fetchers: especies y variantes

Principio: **un fetcher es una abstracción**. No queremos fetchers a medida de una
fuente. Distinguimos:

- **Especie**: la clase Python que sabe *cómo* hablar con un tipo de origen
  (`class_path`). Ej.: `app.fetchers.atom.AtomFetcher` (sindicaciones ATOM/RSS),
  `app.fetchers.rest.RestFetcher` (APIs REST JSON)…
- **Variante**: una fila `Fetcher` que comparte `class_path` con la especie pero
  lleva un bloque `preset_params` (JSONB) con las peculiaridades de una *familia*
  de fuentes. El bloque se edita como unidad y se inyecta en el fetcher genérico.

Orden de resolución de parámetros (en `FetcherFactory.create_from_resource`):
`defaults de la clase → preset_params de la variante → params del recurso → params de ejecución`.

Así un recurso de una familia solo aporta lo verdaderamente suyo (la `url`); las
peculiaridades comunes viven una sola vez en la variante.

## Ejemplo implementado: CODICE 2.07

`PLACSP CODICE (ATOM)` es una **variante** de la especie `AtomFetcher`. Su
`preset_params` encapsula todo lo común de las sindicaciones CODICE del Estado y
de la Comunidad de Madrid (paginación `rel_next`, `field_map` CODICE, parada
incremental `desde=auto`, ritmos). Los 6 manifiestos de esa familia
(`placsp_*`, `madrid_licitaciones`) quedan reducidos a la `url` (Madrid añade
`max_pages`). Cambiar el mapeo CODICE = editar un único bloque.

## Catálogo actual agrupado por especie

| Especie (class_path)            | Fetchers/variantes              | Estado |
|---------------------------------|----------------------------------|--------|
| AtomFetcher                     | Feeds ATOM/RSS (genérico), **PLACSP CODICE (ATOM)** (variante) | OK |
| RestFetcher / paginated_rest / rest_loop / json_timeseries | API REST, API REST Paginada, REST Loop, JSON Time Series | **candidatos a colapsar**: misma especie REST, difieren en paginación/iteración → una especie + variantes |
| html / paginated_html / searchloop_html / url_loop_html / web_tree_fetcher | HTML Forms, HTML Paginated, HTML SearchLoop, URL Loop HTML, Web Tree | familia scraping HTML → revisar solapamientos y unificar en variantes |
| file_download / compressed_file | File Download, Compressed File   | familia adquisición de ficheros → posible variante de descarga+descompresión |
| wfs / wms                       | WFS, WMS                         | familia OGC |
| osm                             | OSM Overpass                     | propia |
| soap                            | Servicios SOAP/WSDL              | propia |

## Fetchers huérfanos (sin recursos que los validen)

Detectados en el audit: `PLACSP Atom`, `PDF_TABLE`, `Portal Files Cataloguer`,
`Portales CKAN`, `Servicios SOAP/WSDL`, `WMS`, `XBRL ZIP`.

- **`PLACSP Atom`**: fila vieja y rota (su módulo `placsp_atom` se eliminó al
  generalizar). Queda **superado por la variante `PLACSP CODICE (ATOM)`** → debe
  retirarse (fila muerta en BD; no está en el seed).
- **El resto**: o se les asigna un recurso real que los ejercite (validándolos), o
  se retiran. Candidatos de fuente para validarlos:
  - `Portales CKAN` → Andalucía (CKAN contratos menores), datos.gob.es.
  - `XBRL ZIP` → depósitos de cuentas / CNMV.
  - `WMS` → un servicio OGC público (IGN, Catastro).
  - `PDF_TABLE` → un boletín con tablas periódicas.
  - `Servicios SOAP/WSDL` → un WS público (p. ej. Catastro OVCServWeb).
  - `Portal Files Cataloguer` → un portal de descargas con índice.

## Fuentes de contratación autonómica y su especie

La mayoría NO usan ATOM; se documentan aquí con el fetcher que les corresponde:

| CCAA            | Formato            | Fetcher/variante adecuado |
|-----------------|--------------------|---------------------------|
| Comunidad de Madrid | Atom CODICE    | **PLACSP CODICE (ATOM)** (ya integrada) |
| País Vasco      | API REST (JSON)    | API REST Paginada (variante "Euskadi") |
| Cataluña        | API Socrata        | API REST (variante "Socrata": `$limit/$offset`, `.json`) |
| Andalucía       | CSV + API ES (CKAN)| Portales CKAN / File Download |
| C. Valenciana, Castilla y León, Canarias, Aragón, Asturias | CSV | File Download (variante CSV) |

Roadmap: definir esas variantes (preset_params) sobre las especies REST/CKAN/CSV
en vez de crear fetchers nuevos, y darles un recurso que las valide.

## Pendiente de gobernanza

`source_classification.clasificar()` clasifica por `fetcher_code`. Al multiplicarse
las variantes conviene que clasifique por **especie (class_path)** para no mantener
listas por variante. (De momento la variante CODICE se añadió a la lista de
"publicación abierta".)

## Categorías de variación (el "origen" de las variantes)

Una variante se desvía del genérico por unos pocos **ejes** bien definidos. Nombrarlos
convierte `preset_params` en algo legible y componible (y, a futuro, editable por
grupos en la UI) en vez de una bolsa opaca:

| Categoría        | Qué aísla                                  | Parámetros típicos |
|------------------|--------------------------------------------|--------------------|
| **Paginación**   | cómo se recorre el conjunto                | `pagination` + sub-bloque |
| **Extracción**   | cómo se sacan los registros de la respuesta| `field_map`, rutas |
| **Incremental**  | cómo se para por novedad                   | `desde`, `date_field` |
| **Cortesía**     | ritmo y límites                            | `delay`, `timeout`, `max_pages` |
| **Transporte/auth** | conexión y credenciales                 | `headers`, api key, OAuth |

### Paginación como categoría (implementada)

`app/fetchers/pagination.py` registra las estrategias con nombre, compartidas por
cualquier fetcher sobre HTTP:

| Estrategia      | Cómo avanza                                  |
|-----------------|----------------------------------------------|
| `none`          | una sola petición                            |
| `query_offset`  | `start_index`/`page_size` hasta página incompleta |
| `page_number`   | `page=N` hasta página vacía                   |
| `rel_next`      | sigue el enlace `next` de la respuesta        |
| `cursor`        | reenvía el token de la siguiente página       |
| `pivot_loop`    | una petición por valor de una lista           |

Esto **explica y disuelve la familia REST**: no son cuatro tecnologías, es una
(HTTP+JSON) con distinta paginación:

| Fetcher actual      | = especie REST + estrategia |
|---------------------|------------------------------|
| API REST            | `none`                       |
| API REST Paginada   | `query_offset` / `page_number` |
| REST Loop           | `pivot_loop`                 |
| JSON Time Series    | `none` (+ extracción propia) |

El registro es puro y testeable (`tests/fetchers/test_pagination.py`). Próximo paso:
hacer que el fetcher ATOM y un fetcher REST genérico lo consuman, y migrar los
recursos de la familia REST a `(REST genérico + estrategia)` antes de retirar las
clases sobrantes.

## Estado de la fusión REST y catálogo de tecnologías

- **REST unificado (aditivo, sin romper)**: `RESTFetcher` ya consume el registro de
  paginación. Sin `pagination` (o `none`) se comporta como siempre (los recursos
  vivos de "API REST" intactos); con estrategia, recorre y acumula `content_field`.
  Absorbe a **API REST Paginada** (= `query_offset`/`page_number`). Migrar sus
  recursos a `(API REST + pagination)` y retirar la clase es un paso posterior
  verificado, recurso por recurso.
- **`REST Loop`** (POST con plantilla + pivote) y **`JSON Time Series`** (extracción
  estadística pesada) NO son solo variantes de paginación: varían por las categorías
  *construcción de la petición* y *extracción*. Se fusionarán cuando esas categorías
  estén formalizadas como la de paginación.
- **Catálogo de tecnologías**: sembradas 23 especies nuevas (GraphQL, SPARQL, SDMX,
  OAI-PMH, OGC API-Features, CSW, WMTS, WCS, STAC, ArcGIS REST, NGSI-LD, SSE,
  WebSocket, MQTT, Kafka, GTFS-RT, webhooks entrantes, navegador headless, OCR PDF,
  ofimática, S3, FTP/SFTP/WebDAV, gRPC) con explicación y casos de uso en su
  descripción larga, marcadas como planificadas hasta implementar su clase.

## Categoría EXTRACCIÓN (implementada)

`app/fetchers/extraction.py` registra estrategias que convierten un payload JSON
decodificado en registros planos (puro y testeable):

| Estrategia        | Qué hace |
|-------------------|----------|
| `passthrough`     | los registros tal cual (tras seleccionar la lista) |
| `field_map`       | aplana cada registro con `{salida: ruta.con.puntos}` |
| `timeseries_long` | formato largo estadístico (dimensiones + puntos) — **absorbe JSON Time Series** |
| `bindings`        | resultados SPARQL (`results.bindings`) |

El `RESTFetcher` la consume vía `extraction` (aditivo: sin valor → parseado tal
cual). Con esto la especie REST cubre ya **paginación** y **extracción**, las dos
categorías que separaban a `API REST Paginada` y `JSON Time Series`. La extracción
de ATOM (field_map sobre rutas de elementos XML) es el primo XML de `field_map`:
mismo concepto, distinto resolvedor; se unificará al migrar ATOM a este registro.

## Categoría CONSTRUCCIÓN DE LA PETICIÓN (implementada)

`app/fetchers/request_building.py` — "qué se envía", como registro de estrategias:

| Estrategia  | Método | Cuerpo |
|-------------|--------|--------|
| `query`     | GET (o el indicado) | sin cuerpo (comportamiento histórico) |
| `json_body` | POST   | plantilla JSON con `{pivot}` — **absorbe REST Loop** |
| `form`      | POST   | formulario con plantilla |
| `graphql`   | POST   | `{query, variables}` |
| `sparql`    | POST   | `query=…` + Accept sparql-results+json |

El `RESTFetcher` la consume vía `request` (aditivo: `query` = como siempre). Con
esto la especie REST cubre ya **las tres categorías** —petición, paginación,
extracción— que separaban a sus variantes:

| Variante histórica | = API REST + (request, pagination, extraction) |
|--------------------|------------------------------------------------|
| API REST           | (query, none, passthrough)                     |
| API REST Paginada  | (query, query_offset/page_number, field_map)   |
| REST Loop          | (json_body, pivot_loop, …)                      |
| JSON Time Series   | (query, none, timeseries_long)                  |

`pivot_loop` expone el valor iterado en el spec para que `json_body` lo plantille
en el cuerpo. **FUSIÓN REALIZADA**: `seed_fetchers._colapsar_familia_rest` repunta
los recursos de las tres variantes a `API REST` (añadiendo los params mapeados;
para JSON Time Series copia `content_field` desde `root_path`) y retira (soft-delete)
las filas variantes. Las clases `paginated_rest.py` / `rest_loop.py` /
`json_timeseries.py` se han eliminado: la especie `API REST` las cubre por completo.
Mapa aplicado: Paginada→(query, page_number start_page=0, passthrough);
Loop→(json_body, pivot_loop, passthrough); Time Series→(query, none, timeseries_long).
A verificar en el primer despliegue: que cada recurso migrado siga devolviendo los
mismos registros (sobre todo REST Loop, cuya extracción de respuesta era a medida).
