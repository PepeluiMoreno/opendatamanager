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
