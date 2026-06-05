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
