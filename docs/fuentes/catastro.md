# Catastro (Sede Electrónica / INSPIRE Download Services) — ficha de fuente

> **Estado**: estructura **verificada en vivo el 2026-06-18** contra el servicio real
> (ver "Verificado en vivo" abajo). El `child_fetcher`/`entry` y el feed CP están
> confirmados; BU/AD por confirmar en detalle.

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

## ⚠️ El feed nacional FEDERA varios productores (verificado 2026-06-19)

El feed de servicio CP **no es solo DGC**: sus `<entry>` enlazan a sub-feeds de
**productores distintos** (las diputaciones forales publican su propio INSPIRE).
Las 8.069 hojas se reparten así:

| Productor (host) | Hojas | Estructura de la hoja | GML interno |
|---|---|---|---|
| **DGC peninsular** (`www.catastro.hacienda.gob.es`) | 7.611 | `/CP/{prov}/{NNNNN-NOMBRE}/A.ES.SDGC.CP.{NNNNN}.zip` | `*.cadastralparcel.gml` (+ zoning) |
| **Navarra** (`filescartografia.navarra.es`) | 342 | `.../files/CP_Navarra_{n}.gml.zip` (por **tesela**) | `CP_Navarra_{n}.gml` |
| **Bizkaia** (`apli.bizkaia.eus`) | 112 | `/apps/Danok/INSPIRE/ES.BFA.CP.{NNN}.zip` (por municipio) | `ES.BFA.CP.gml` |
| **Araba** (`geo.araba.eus`) | 3 | `/deskargak/INSPIRE/CP/GML/{crs}/CP_{crs}_GML.zip` (por **CRS**) | único |
| **Gipuzkoa** (`b5m.gipuzkoa.eus`) | 1 | `/inspire/download/GML/ES.GFA.CP.zip` (provincia entera) | único |

Implicaciones: (a) el GML interno **no** se llama igual en todos → el `entry`
es **por productor** (`*.cadastralparcel.gml` solo en DGC; `*.gml` en los
forales, que traen un único GML); (b) Navarra agrupa por tesela y Araba por CRS,
no por municipio → su dimensión no es "municipio" aunque el descubridor la
nombre así por heurística (renómbrese al promover si importa).

## Descubrimiento: `propose()` (no `discover()`+`infer()`)

El `infer()` genérico **no sirve** para este feed: el código de municipio varía
en DOS átomos correlacionados (carpeta `02001-ABENGIBRE` **y** filename
`...CP.02001.zip`), y el infer —que colapsa de a un átomo— deja ~1 candidato por
municipio (se midió: **7.617 propuestas** de 8.069 hojas). Además mezclaba los
cinco productores.

Por eso el **Crawler ATOM implementa `propose()`**: agrupa las hojas por
**productor** (netloc) y construye él mismo el `path_template` y las dimensiones
→ **un candidato autosuficiente por productor** (5 en total), con
`target_fetcher_code=Crawler ATOM` y `target_params` (entry/inner_format/
cortesía). El productor primario (mismo host que el feed) hereda el `entry` del
padre; los federados usan `*.gml`. El `FetcherManager` llama a `propose()` antes
que a `discover()+infer()` cuando la especie lo expone.

> Bug colateral corregido: el clasificador tomaba la **provincia `02`–`12` como
> `{month}`**. Ahora un mes numérico solo se acepta si hay un `{year}` más
> superficial en el path (`template_path_segments`).

## Fetchers que usa

| Pieza | Especie ODM | Rol |
|---|---|---|
| Descubrimiento | **Descubridor ATOM** (`AtomDownloadDiscoverer`) | Recorre la jerarquía servicio→gerencia→ficheros y **propone un recurso-hijo por fichero hoja** (ZIP), con la URL ya resuelta. Filtra por municipio. Agnóstico de dominio. |
| Cortesía | **Throttle por host** (opt-in, en `base._request`) | Evita el veto. Se fija en el descubridor y **se propaga a los hijos**. |
| Descarga + parseo (hoja) | **Compressed File** con `inner_format=gml` | Baja el ZIP, extrae el `.gml` y lo **parsea a registros con geometría GeoJSON** (ver abajo). |

### Descubridor ATOM — parámetros clave

- `url`: feed de servicio (nivel superior).
- `filtro_incluir`: subcadenas que debe contener el título/id/href de la hoja para
  proponerse. Para Catastro = **códigos de municipio** (p. ej. `["11020"]`). Vacío = todos.
- `leaf_exts`: extensiones que cuentan como fichero (def. `zip,gz,gml,tar,7z,rar,tgz`).
- `max_depth`: niveles a descender (0 = auto por type/extensión del `<link>`).
- `child_fetcher` / `child_params`: especie y params de los hijos (p. ej.
  `{"inner_format": "gml", "entry": "*.gml"}`).
- `rate_limit_per_second` / `request_delay_ms` / `max_per_hour`: cortesía (se propaga).

**Throttle recomendado para Catastro**: `max_per_hour=3500`, `rate_limit_per_second=1`.

### Payload GML → JSONL (DECIDIDO 2026-06-18)

ODM **parsea el GML a registros** — la misma salida que cualquier otro recurso
(JSONL) — con la geometría como **GeoJSON** y las coordenadas **nativas** (sin
reproyectar), más `srsName`. Sigue siendo **productor-neutro**: conserva los
nombres originales (`nationalCadastralReference`, `areaValue`, …) y NO aplica la
semántica de SIPI (eso lo hace SIPI).

- **Especie-hoja**: `Compressed File` con `inner_format=gml` (+ `entry=*.gml`).
  Baja el ZIP, extrae el `.gml` y lo parsea con el nuevo `app/fetchers/gml_parser.py`
  (stdlib, **sin GDAL**): Point / LineString / Polygon / MultiSurface→MultiPolygon, etc.
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

## Cómo se configurará (manifests — PENDIENTE de luz verde)

Un recurso **Descubridor ATOM** por tema, p. ej. (forma orientativa):

```json
{
  "name": "Catastro INSPIRE - Parcelas (CP)",
  "fetcher": "Descubridor ATOM",
  "collection": "Inmuebles religiosos en España",
  "active": true,
  "params": [
    { "key": "url", "value": "https://www.catastro.hacienda.gob.es/INSPIRE/CadastralParcels/ES.SDGC.CP.atom.xml" },
    { "key": "filtro_incluir", "value": "", "is_external": true },
    { "key": "child_fetcher", "value": "Compressed File" },
    { "key": "child_params", "value": "{\"inner_format\": \"gml\", \"entry\": \"*.cadastralparcel.gml\"}" },
    { "key": "max_per_hour", "value": "3500" },
    { "key": "rate_limit_per_second", "value": "1" }
  ]
}
```

El descubridor propaga `child_fetcher`/`child_params` a cada hijo, así que cada ZIP
municipal nace como un recurso **Compressed File** que ya sabe extraer y parsear el GML.

BU y AD: idéntico cambiando `url`. **El manifest no lleva ni un campo de SIPI.**

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
