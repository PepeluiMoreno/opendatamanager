# BDNS / SNPSAP — ficha de fuente (verificada)

**Regla de esta ficha**: todo lo que figura aquí procede de la especificación
OpenAPI oficial (archivada junto a este documento) o de pruebas en vivo contra el
API. Nada está escrito de memoria. Verificado: 2026-06-05.

## Especificación oficial

- Swagger UI: `https://www.infosubvenciones.es/bdnstrans/doc/swagger`
- OpenAPI v1 (52 endpoints): `https://www.infosubvenciones.es/bdnstrans/estaticos/doc/snpsap-api.json`
  → archivado: `docs/fuentes/bdns/snpsap-api-v1.1.0.json`
- OpenAPI v2.1 "presidencia" (3 endpoints: `/catalogo/{dataset}`,
  `/convocatoria/{id}`, `/listadoconvocatoria`):
  `https://www.infosubvenciones.es/bdnstrans/estaticos/doc/snpsap-api-presidencia-v2.1.json`
  → archivado: `docs/fuentes/bdns/snpsap-api-presidencia-v2.1.json`
- Base del API: `https://www.infosubvenciones.es/bdnstrans/api` (espejos en
  infosubvenciones.gob.es y pap.hacienda.gob.es, según el bundle del portal).

## Dos familias de endpoints (v1)

**Catálogos** (sin paginación; devuelven la lista/árbol completo): `organos`,
`organos/agrupacion`, `organos/codigo`, `organos/codigoAdmin`, `regiones`,
`sectores`, `actividades`, `finalidades`, `instrumentos`, `objetivos`,
`reglamentos`, `beneficiarios`, `terceros`, `enlaces`.

- `/organos`: `idAdmon` **REQUERIDO**, enum `C | A | L | O` (estatal, autonómica,
  local, otros); `vpd` opcional (portal, p. ej. `GE`). Respuesta: árbol
  `[{id, descripcion, children: [...]}]`. Probado en vivo: C=22 raíces,
  A=19, L=50, O=214. **No admite** `page`/`pageSize` (400).

**Búsquedas** (paginadas, estilo Spring): `convocatorias/busqueda`,
`concesiones/busqueda`, `ayudasestado/busqueda`, `minimis/busqueda`,
`sanciones/busqueda`, `partidospoliticos/busqueda`,
`grandesbeneficiarios/busqueda`, `planesestrategicos/busqueda`,
`convocatorias/ultimas`.

- Paginación: `page` (desde 0), `pageSize`, `order` (enum por endpoint),
  `direccion` (`asc|desc`).
- Respuesta: `{content: [...], totalPages, totalElements, last, first, number, ...}`
  → en ODM: `pagination=page_number`, `start_page=0`, `content_field=content`.
- Filtros ricos por endpoint (del spec): `descripcion(+TipoBusqueda)`,
  `numeroConvocatoria`, `fechaDesde/fechaHasta`, `tipoAdministracion (C|A|L|O)`,
  `organos[]`, `mrr`, `contribucion`, etc.

Cada búsqueda tiene su gemelo `/exportar` (descarga masiva; parámetros en el spec —
no verificado en vivo todavía).

## Recursos ODM actuales

`manifests/bdns_organos.json`: 4 recursos (uno por `idAdmon`), fetcher `API REST`,
`query_params={vpd: GE, idAdmon: X}`, sin paginación, passthrough. Probados con el
RESTFetcher real contra el API real.

## Candidatos de cosecha (pendientes, mapping ya verificado)

`convocatorias/busqueda` y `concesiones/busqueda` (núcleo del dato de subvenciones),
`minimis`, `ayudasestado`, `sanciones`, `partidospoliticos`, `grandesbeneficiarios`
→ todos como variantes de `API REST` con `(page_number desde 0, content,
filtros del spec)`. El detalle de cada filtro está en el spec archivado.

## Intervalo temporal como parámetro de runtime (verificado 2026-06-15)

Las búsquedas aceptan `fechaDesde`/`fechaHasta`. El RESTFetcher resuelve ahora
marcadores `{token}` en los valores de `query_params` con los `execution_params`
de la ejecución (igual semántica que `{pivot}`): el recurso declara
`query_params={"fechaDesde":"{fecha_desde}","fechaHasta":"{fecha_hasta}", "vpd":"GE"}`
y la ejecución aporta `fecha_desde`/`fecha_hasta`. Si un token no tiene valor, el
query-param se OMITE → sin intervalo = corpus íntegro; con intervalo = ventana.
Esto hace el backfill histórico una cuestión de `execution_params`, sin tocar el
recurso.

- **Formato de fecha: `dd/mm/yyyy`** (probado en vivo). El ISO `aaaa-mm-dd` da
  `400 ERR_VALIDACION`.
- **Cobertura por `fechaConcesion`** (probado, `/concesiones/busqueda`, vpd=GE):
  total sin filtro ≈ **27.011.959**; por año: 2019–2021 → **0**; 2022 → 1.129.023;
  2023 → 1.149.635; 2024 → 1.156.212; 2025/2026 en el mismo orden de magnitud.
  Es decir, por fecha de concesión el SNPSAP solo devuelve **2022 en adelante**.

## Recursos de búsqueda (manifests/bdns_busquedas.json)

8 recursos `API REST`, paginación `page_number` (`page` desde 0, `pageSize`,
`content_field=content`), con la ventana temporal de runtime: convocatorias,
concesiones, mínimis, ayudas de Estado, grandes beneficiarios, sanciones,
partidos políticos, planes estratégicos. Backfill por año:
`execution_params={"fecha_desde":"01/01/2022","fecha_hasta":"31/12/2022"}`.

## Paginación profunda y orden estable (verificado 2026-06-15, año a año hacia atrás)

Probando la extracción año a año (2025 primero) salieron dos lecciones, ambas
resueltas alineándose con la config que ya usaba ODM:

1. **El `order` debe ser una clave ÚNICA/monótona, no una con empates.** Con
   `order=fechaConcesion` la paginación profunda de un dataset grande se rompe
   (la página 2 da timeout) porque hay millones de filas con la misma fecha. Con
   `order=codConcesion` (clave única) la paginación profunda sobrevive (página 20+
   sin timeout). Por eso el recurso de convocatorias que SÍ funcionaba usaba
   `numeroConvocatoria`. El manifest fija ahora una clave única por endpoint:
   concesiones/ayudasestado/partidospoliticos → `codConcesion`; convocatorias/
   minimis → `numeroConvocatoria`; resto → la más estable disponible.

2. **`fechaDesde/fechaHasta` deben ir en `query_params`** (el RESTFetcher solo
   envía `query_params`; las claves sueltas del recurso NO se enviaban — por eso
   los `fechaDesde/fechaHasta=2026` sueltos no filtraban y ODM acababa trayendo
   los ~2M más recientes, todos de 2026, hasta que la paginación se agotaba).

**Volumen real por año (`/concesiones/busqueda`, vpd=GE, verificado):**
2024 ≈ 1.156.212 (normal, paginable de un tirón). **2025 ≈ 19.667.739** —
anómalo: el grueso está volcado a fin de año (dic-2025 ≈ 6,06M; gran parte con
`fechaConcesion=2025-12-31`, típico de cargas masivas tipo PAC). 2026 (parcial) ≈ 3,9M.

**Estrategia de backfill:** lanzar ejecuciones por ventana, año a año hacia atrás,
y **sub-trocear por mes los años de gran volumen** (2025 sin trocear no es práctico
por offset; por mes cada ventana pagina independiente y rápido en cabeza). El
intervalo es runtime: `execution_params={"fecha_desde":"01/03/2025","fecha_hasta":"31/03/2025"}`.
El barrido pesado corre en ODM (background + scheduler), no en cliente.

## Serie por ejercicio + colección (seed_bdns_ejercicios.py)

`seed_bdns_ejercicios.py` da de alta, por cada búsqueda con ventana temporal:
una COLECCIÓN (recurso padre, `genera_colecciones=True`, corre con fechas de
runtime y representa el histórico) y un RECURSO HIJO por EJERCICIO
(`parent_resource_id` → colección) acotado a su año con `fecha_desde`/`fecha_hasta`.
Los ejercicios NO se hardcodean: se detectan sondeando el SNPSAP de hoy hacia
atrás hasta el primero con registros (concesiones: 2022→2026). Idempotente
(upsert por nombre). Ojo: la fecha se envía al SNPSAP en dd/mm/yyyy y SOLO filtra
con `fechaDesde`/`fechaHasta` (camelCase); `fecha_desde`/`fecha_hasta` snake_case
son ignoradas por la API y devuelven el corpus íntegro — por eso el fetcher mapea
los params de runtime `fecha_desde`→`fechaDesde`.

## Concurrencia y troceo mensual (backfill)

El trabajo es I/O-bound (HTTP + escritura de dataset) → paralelismo con HILOS,
acotado. `seed_bdns_backfill.py` usa un pool (`--workers`, tope =
`max_concurrent_processes` de AppConfig, def. 3), cada worker con su propia sesión;
ejecuta las ventanas de más reciente a más antigua vía FetcherManager.run (camino
del scheduler, sin cooldown/cuota). La cortesía por página la pone el fetcher
(`delay_between_pages`); no se paraleliza dentro de un mismo crawl.

Donde la concurrencia rinde es entre ventanas pequeñas: `seed_bdns_ejercicios.py`
trocea en 12 hijos MENSUALES los años de gran volumen (> umbral, def. 2M; p. ej.
concesiones 2025 ≈ 19,67M, dic ≈ 6M). Ventanas mensuales = offsets más someros
(páginas más rápidas) + N unidades paralelizables. `--mensual` fuerza el troceo;
`--mensual-umbral N` ajusta el corte.
