# PENDIENTE: recursos derivados (cruce de datasets)

Aparcado el 2026-06-05 por decisión de producto: de momento se cosechan las piezas
crudas y el cruce se hace fuera de ODM. Este documento conserva el diseño y los
hechos verificados para retomarlo.

## Diseño acordado: especie interna `CruceDatasets`

No rompe el sentido de ODM si es declarativo: ODM ya tiene derivación post-cosecha
de fuente única (`DerivedDatasetConfig`, upsert), dependencia de datos entre
recursos (`pivot_source_odmgr_query`) y recursos padre/hijo (`parent_resource_id`).
La pieza que falta es una especie cuyo "transporte" es el propio almacén de ODM:

- `class_path`: `app.fetchers.cross_dataset.CrossDatasetFetcher` (a crear)
- Params declarativos: `left_resource`, `right_resource`, `left_key`, `right_key`
  (rutas con puntos), `join` (enum `enrich|inner|left`), `via` (tabla puente
  opcional), `select` (mapa de campos de salida).
- Gratis por ser un recurso: schedule, ejecuciones, salud, versionado, linaje.
- Frescura v1 por cron (correr tras sus fuentes); mejora: señal "fuente más nueva
  que derivado".

## Caso motivador: subvenciones ↔ organismos ↔ licitaciones (VERIFICADO)

| Pieza | Clave | Verificación |
|---|---|---|
| PLACSP licitaciones | DIR3 nativo (`<cbc:ID schemeName="DIR3">`) | feed vivo 2026-06-05 |
| BDNS órganos | id interno; `/organos/codigo?codigo=<DIR3>` → `{tipoAdmon, ids[]}` | probado: L01380435 → [3368] |
| BDNS convocatorias | órgano solo como texto nivel1/2/3 + `codigoInvente` (a veces null); búsqueda filtra por `organos[]` (ids internos) | spec + API vivo |

DIR3 es la espina dorsal. El puente BDNS se construye: DIR3 → `/organos/codigo` →
ids internos → convocatorias por órgano. `codigoInvente` (Inventario de Entes) como
clave secundaria cuando exista.

## Pasos al retomar

1. ~~Especie `CruceDatasets` + seed + tests~~ **HECHO (2026-06-06)** y
   **formalizado**: direccionamiento por NOMBRE de recurso (`left_resource`/
   `right_resource`, string o lista con unión; la query se deriva en runtime
   con `dataset_query_name`, así que sobrevive a regeneraciones) y linaje a
   máquina en `opendata.resource_dependency` (sincronizado por el manager en
   cada ejecución del derivado; base para la señal "fuente más nueva que
   derivado"). `left_query`/`right_query` quedan como vía avanzada sin linaje.
   Detalle previo:
   `app/fetchers/cross_dataset.py` (núcleo puro `cruzar` + fetcher sobre la API
   de datos), matriculada en el catálogo, tests en
   `tests/fetchers/test_cross_dataset.py`. Primer uso: recurso derivado
   "Órganos Convocantes con DIR3" en `manifests/bdns_organos.json` (inactivo
   hasta fijar left_query/right_query en prod).
2. ~~Recurso puente `{dir3, ids_bdns}`~~ **HECHO (2026-06-05)**: `pivot_source_odmgr_query`
   portado a RESTFetcher (módulo compartido `app/fetchers/pivot_sources.py`),
   `pivot_field_out` para anotar el pivote en cada fila, respuesta-objeto por pivote
   soportada. Recurso en `manifests/bdns_puente_dir3.json` — al importar en prod,
   fijar `pivot_source_odmgr_query`/`pivot_source_field` con la query del dataset
   DIR3 cosechado. Verificado en vivo (L01280796→2993, L01380435→3368, 204 omitido).
3. Cruce subvención↔órgano(DIR3)↔licitación como recurso `CruceDatasets` —
   ya posible declarativamente: convocatorias (left, por ids de órgano vía
   búsqueda por organos[]) × puente (dir3) × licitaciones PLACSP (dir3 nativo).
   Falta solo cosechar convocatorias por órgano y declarar los dos cruces.

## Cosecha cruda (en curso, fuera de este pendiente)

DIR3 (catálogo oficial), DIR3 en el field_map del preset PLACSP, y
convocatorias/concesiones de BDNS — ver manifests/.
