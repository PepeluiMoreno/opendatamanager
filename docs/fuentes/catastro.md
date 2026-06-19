# Catastro (Sede Electrónica / INSPIRE Download Services) — ficha de fuente

> **Estado**: estructura **verificada en vivo el 2026-06-18** contra el servicio real
> (ver "Verificado en vivo" abajo). El feed CP y la hoja ZIP→`.cadastralparcel.gml`
> están confirmados; BU/AD por confirmar en detalle.
>
> **Fetcher real**: **"Crawler ATOM"** (`app/fetchers/atom_crawler_fetcher.py`,
> `AtomCrawlerFetcher`). Doc revisado el 2026-06-19 para alinearlo con el código:
> versiones anteriores hablaban de un "Descubridor ATOM"/`AtomDownloadDiscoverer`
> con `child_fetcher`/`child_params` que **nunca existió**. El modelo real es
> **dual-modo, espejo de Web Tree** (ver abajo).

## ⚠️ Códigos DGC ≠ códigos INE (clave para el filtro)

El feed usa la **numeración municipal del DGC**, que NO siempre coincide con el INE.
Verificado: la capital **Cádiz sale como `11900`** (INE 11012). Por tanto `filtro_incluir`
debe llevar **códigos DGC**, y **SIPI** (que maneja INE) necesitará un **mapeo INE↔DGC**
para filtrar por municipio.

Además, **algunos municipios no se publican** en el feed: p. ej. **Jerez de la Frontera
(INE 11020) NO aparece** en `ES.SDGC.CP.atom_11.xml` (37 de ~45 municipios de Cádiz) ni
existe por descarga directa (URL 11020 → soft-404 HTML de 15257 bytes). El descubridor,
que se basa en el feed, **no cogerá esos municipios**; si alguno hace falta, necesita una
fuente/recurso aparte. (Nota: 11400 es el *código postal* de Jerez, no un código catastral.)

## Qué es

La **Sede Electrónica del Catastro** (Dirección General del Catastro, DGC) publica los
datos catastrales como **servicios de descarga predefinida INSPIRE** en formato **ATOM**
(Atom Download Service / OpenSearch).

- **Host**: `www.catastro.hacienda.gob.es`
- **Formato del payload**: GML 3.2.1, empaquetado en ZIP.
- **Granularidad**: **municipio** (un fichero por municipio).
- **Refresco**: ~2 veces al año.
- **Versionado**: cada entrada trae `beginLifespanVersion`/`updated` → permite **caché
  por versión** (no re-descargar lo que no cambió).
- **Jerez de la Frontera = `11020`** (provincia de Cádiz, `11`).

### Cupo duro (la razón del throttle)

Los servicios libres del Catastro **limitan a ~3.600 peticiones/hora por IP** y, al
superarlo, **deniegan el servicio durante ~4 horas**. No devuelven 429: simplemente
vetan. Contra eso no vale reaccionar (backoff): hay que **no llegar nunca**. Por eso
ODM aplica un *throttle proactivo por host* (ver abajo).

## Cómo lo trata ODM

**Principio innegociable: ODM es productor neutro.** Descubre *qué* descargar y *desde
dónde*; **no** parsea el GML ni lo mapea a campos de SIPI. El mapeo
(`nationalCadastralReference`→`referencia_catastral`, `conditionOfConstruction`→
`estado_conservacion`, …) y el `GML → PostGIS → ST_Contains` es **del consumidor (SIPI)**.

### La jerarquía ATOM (2 niveles)

```
feed de SERVICIO (ES.SDGC.CP.atom.xml)
   └─ <entry> → feed por GERENCIA/territorio (provincia)
         └─ <entry> → fichero ZIP municipal (A.ES.SDGC.CP.<R|U>.<MUNI>.zip → .gml dentro)
```

- **CP** separa **urbana (U)** y **rústica (R)** → varios ZIP por municipio.
- **BU** trae **tres GML** por unidad (building / buildingpart / otherconstruction).
- `AtomFetcher` ("Feeds ATOM/RSS") **no** sirve aquí: su `rel_next` es paginación
  *horizontal* de un mismo feed, no desciende por enlaces *por-entrada* a sub-feeds.

## Fetcher que usa: "Crawler ATOM" (un solo fetcher, dos modos)

Lo sirve una **única especie**, **"Crawler ATOM"** (`AtomCrawlerFetcher`), que es el
**espejo de Web Tree** pero sobre una jerarquía de *feeds* en vez de HTML. **No hay
recursos hijos "Compressed File" ni `child_fetcher`/`child_params`**: el mismo fetcher
hace descubrimiento y extracción, reutilizando *internamente* la maquinaria de
Compressed File (`_extract_zip/_extract_gz/...` + `parse_structured_file` +
`gml_parser.parse_gml`), sin duplicar lógica.

| Modo | Cuándo | Qué hace |
|---|---|---|
| **discover()** | recurso-madre (`genera_colecciones: true`), con **Run** | Recorre los feeds (servicio→gerencia→ficheros) en anchura y devuelve las **URLs hoja** `[{"url","file_type",...}]`. El `FetcherManager` las pasa a `infer()`, que **agrupa por `path_template`** y detecta el código de municipio como **dimensión** → **UN candidato dimensionado** por dataset. **8.000 ficheros NO son 8.000 recursos.** |
| **stream()** | recurso hijo promovido | Recibe `_matched_urls`/`_dimensions`/`_path_template` (inyectados por el manager) y, por cada URL, **baja el ZIP, extrae el `.gml` y lo parsea a registros con geometría GeoJSON**. Cada registro se etiqueta con la dimensión (municipio, re-extraída del `path_template`) y con `_source_file_url`. Salida JSONL homogénea, idéntica a cualquier otro recurso. |

- **Cortesía (throttle por host)**: opt-in, vive en `base._request` (`throttle.py`).
  Se aplica en **ambos** modos porque ambos usan `self._request`. Es **por host
  (netloc)**, no por instancia: varios workers y varios recursos contra el mismo host
  comparten el mismo presupuesto, igual que cuenta el límite por IP del servidor.
- **Tolerancia a fallos**: un municipio caído/corrupto en `stream()` se **omite con
  warning**; no tumba la serie.
- **El botón Test** sobre la madre usa `_preview_limit`: descubre y extrae unas pocas
  hojas para una cata.

### Parámetros clave

**Descubrimiento (`discover`)**:
- `url`: feed de servicio (nivel superior). **Obligatorio.**
- `filtro_incluir`: subcadenas que debe contener título/id/href de la hoja para
  proponerse. Para Catastro = **códigos de municipio DGC** (p. ej. `["11020"]`).
  Vacío = todos. Suele marcarse `is_external: true` (lo fija el consumidor, SIPI).
- `leaf_exts`: extensiones que cuentan como fichero hoja (def.
  `zip,gz,gml,tar,7z,rar,tgz`).
- `max_depth`: niveles a descender (`0` = auto por type/extensión del `<link>`).
- `max_feeds`: tope de feeds a leer en el descenso (def. `500`).

**Extracción (`stream`)** — se propagan al hijo promovido:
- `entry`: glob del fichero a extraer dentro del contenedor (p. ej.
  `*.cadastralparcel.gml`). Imprescindible cuando el ZIP trae varios GML.
- `inner_format`: formato del fichero interno (`gml`). Si se omite, se infiere de la
  extensión de `entry`.
- `format`: formato del contenedor (`zip`/`gz`/`tar`/...); si se omite se infiere de la URL.
- `batch_size` (def. `1000`), `file_delay`, `headers`, `timeout`.

**Cortesía (throttle, ambos modos)**:
- `rate_limit_per_second` y/o `request_delay_ms`: intervalo mínimo entre peticiones.
- `max_per_hour`: ventana horaria deslizante (la reja que evita el veto).

**Throttle recomendado para Catastro**: `max_per_hour=3500`, `rate_limit_per_second=1`.

### Payload GML → JSONL (DECIDIDO 2026-06-18)

ODM **parsea el GML a registros** — la misma salida que cualquier otro recurso
(JSONL) — con la geometría como **GeoJSON** y las coordenadas **nativas** (sin
reproyectar), más `srsName`. Sigue siendo **productor-neutro**: conserva los
nombres originales (`nationalCadastralReference`, `areaValue`, …) y NO aplica la
semántica de SIPI (eso lo hace SIPI).

- **Lo hace el propio "Crawler ATOM"** en `stream()`: con `inner_format=gml` (+
  `entry=*.cadastralparcel.gml`) baja el ZIP, extrae el `.gml` y lo parsea con
  `app/fetchers/gml_parser.py` (stdlib, **sin GDAL**): Point / LineString / Polygon /
  MultiSurface→MultiPolygon, etc. Reutiliza la extracción de Compressed File, no la duplica.
- **SIPI** consume los registros por la API y hace
  `ST_SetSRID(ST_GeomFromGeoJSON(geometry), <srid de srsName>)` (+ reproyección si
  procede). Mucho más ligero que un ETL con `ogr2ogr`.

**Avisos**:
- *Orden de ejes*: se respeta el del GML (no se intercambia). Para UTM ETRS89
  (EPSG:258xx, eje E,N) coincide con GeoJSON; para CRS geográficos (lat,lon) el
  consumidor lo corrige con `srsName`.
- *ZIP con varios GML* (caso **BU**: building / buildingpart / otherconstruction):
  `entry` debe apuntar a uno concreto (un recurso por GML), porque `*.gml` casaría
  varios y daría error de ambigüedad.
- Si SIPI necesitara el **GML oficial íntegro** (motivo legal), úsese passthrough.

## Recursos obtenibles

| Tema | Feed de servicio (a confirmar) | Contenido | Prioridad |
|---|---|---|---|
| **CP** — Parcelas catastrales | `.../INSPIRE/CadastralParcels/ES.SDGC.CP.atom.xml` | Referencia catastral (RC) + geometría de parcela; urbana/rústica | **Imprescindible** (es la RC) |
| **BU** — Edificios | `.../INSPIRE/Buildings/ES.SDGC.BU.atom.xml` | Estado constructivo / año / uso (3 GML) | Recomendable |
| **AD** — Direcciones | `.../INSPIRE/Addresses/ES.SDGC.AD.atom.xml` | Direcciones postales geolocalizadas | Opcional |

## Cómo se configura (manifests)

Un recurso **Crawler ATOM** por tema. Forma real, alineada con
`manifests/catastro_cp_parcelas.json`:

```json
{
  "name": "Catastro INSPIRE - Parcelas (CP)",
  "fetcher": "Crawler ATOM",
  "genera_colecciones": true,
  "active": true,
  "clase_fuente": "api_abierta",
  "params": [
    { "key": "url", "value": "https://www.catastro.hacienda.gob.es/INSPIRE/CadastralParcels/ES.SDGC.CP.atom.xml" },
    { "key": "filtro_incluir", "value": "", "is_external": true },
    { "key": "inner_format", "value": "gml" },
    { "key": "entry", "value": "*.cadastralparcel.gml" },
    { "key": "rate_limit_per_second", "value": "1" },
    { "key": "max_per_hour", "value": "3500" }
  ]
}
```

`genera_colecciones: true` marca la madre como **Colección** (modo `discover`). Al
ejecutarla, el manager infiere los datasets dimensionados y promueve los hijos, que
heredan `entry`/`inner_format` y el throttle y corren en modo `stream`. **El manifest
no lleva ni un campo de SIPI** (productor neutro).

BU y AD: idéntico cambiando `url` (y el `entry`, ver tabla de recursos). **BU trae 3
GML por ZIP**, así que necesita **un recurso por GML** (un `entry` distinto cada uno),
porque un glob `*.gml` casaría varios y daría ambigüedad.

## Verificado en vivo (2026-06-18)

- **Feed de servicio CP**: 200 OK, 56 `<entry>` = 56 gerencias provinciales, cada una
  con `<link rel="enclosure" type="application/atom+xml" href=".../NN/ES.SDGC.CP.atom_NN.xml"/>`
  → sub-feed provincial. El descubridor lo trata como feed (desciende). ✔
- **Sub-feed provincial** (Cádiz, `11`): 37 `<entry>`, una por municipio, con
  `<link rel="enclosure" href=".../A.ES.SDGC.CP.<DGC>.zip" type="application/atom+xml"/>`.
  Ojo: el `type` viene mal puesto (`atom+xml`) pero la **extensión `.zip`** hace que el
  descubridor lo clasifique como hoja. ✔
- **ZIP municipal** (`11001`): contiene **`*.cadastralparcel.gml`** (las parcelas) +
  `*.cadastralzoning.gml` (zonificación) + `*.MD..xml` (metadatos). Por eso
  `entry=*.cadastralparcel.gml`. ✔
- **Soft-404**: las URLs inexistentes devuelven `200` + HTML de 15257 bytes (no 404);
  las reales dan `206`/`PK`. Útil para validar.

## Lo que falta por verificar

1. **BU/AD** en detalle (BU trae 3 GML por ZIP → un recurso por GML).
2. **Orden de ejes** del GML por CRS contra un fichero real (UTM ETRS89 vs geográfico).
3. **Mapeo INE↔DGC** (lado SIPI) para poder filtrar por municipio.
