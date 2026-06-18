# Catastro (Sede Electrónica / INSPIRE Download Services) — ficha de fuente

> **Estado**: la estructura ATOM de 2 niveles, el cupo por IP y los temas CP/BU/AD
> proceden de la documentación oficial INSPIRE de la DGC. **Las URLs exactas de los
> sub-feeds y la forma precisa de cada `<entry>` están PENDIENTES de verificación en
> vivo** antes de sembrar manifests (no se ha golpeado el servicio real en esta sesión).
> Lo verificado a fecha de hoy se marca como tal; el resto es "a confirmar".

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
    { "key": "filtro_incluir", "value": "[\"11020\"]", "is_external": true },
    { "key": "child_fetcher", "value": "Compressed File" },
    { "key": "child_params", "value": "{\"inner_format\": \"gml\", \"entry\": \"*.gml\"}" },
    { "key": "max_per_hour", "value": "3500" },
    { "key": "rate_limit_per_second", "value": "1" }
  ]
}
```

El descubridor propaga `child_fetcher`/`child_params` a cada hijo, así que cada ZIP
municipal nace como un recurso **Compressed File** que ya sabe extraer y parsear el GML.

BU y AD: idéntico cambiando `url`. **El manifest no lleva ni un campo de SIPI.**

## Lo que falta por verificar (antes de sembrar)

1. URLs reales de los feeds de servicio y de los sub-feeds de gerencia.
2. Forma de cada `<entry>` (¿un ZIP = una entrada, o varios `<link>` por entrada?)
   y si los `<link>` traen `type` (zip/atom) — el descubridor clasifica por eso.
3. Si el servicio exige `User-Agent` u otras cabeceras (como PLACSP).
4. ~~La decisión de payload GML~~ → **RESUELTO**: GML→JSONL vía `Compressed File` +
   `inner_format=gml` (parser propio, sin GDAL). Falta confirmar contra un GML real
   el orden de ejes por CRS y el reparto de GML en los ZIP de BU.
