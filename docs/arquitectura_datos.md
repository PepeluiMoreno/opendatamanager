# ODM — Documento técnico: del origen al dataset derivado

Consolida las aclaraciones de las sesiones de junio de 2026 sobre cómo ODM
trata los datos desde la fuente hasta los datasets derivados. Es el documento
de referencia conceptual; el detalle operativo vive en los docs enlazados.

## 1. El pipeline en una frase

Un **Resource** declara cómo cosechar una fuente (especie de fetcher + params,
opcionalmente vía un **perfil** de la especie). Cada ejecución hace *stream* de
registros normalizados a un fichero de **staging JSONL**, sobre el que pueden
aplicarse post-pasadas (dedup); el **DatasetBuilder** convierte ese staging en
un **Dataset versionado** (`data.jsonl` + checksum), que queda consultable por
la **API GraphQL de datos** con un nombre de query derivado del nombre del
recurso (`dataset_query_name`, p. ej. "PLACSP - Licitaciones" →
`placspLicitaciones`).

## 2. Formatos de fuente

### 2.1 Atom y CODICE (PLACSP)

**Atom** es el formato estándar de sindicación web: un XML `<feed>` con
`<entry>` y enlaces de navegación (`rel="next"`). La administración española lo
usa para publicar datos incrementales; PLACSP publica así sus licitaciones, con
el detalle de cada expediente incrustado como documento **CODICE**
(adaptación española de UBL/OASIS para contratación pública:
`ContractFolderStatus` con namespaces `cac:`/`cbc:`, vocabulario controlado de
órgano DIR3, CPV, importes, estados...).

El `AtomFetcher` recorre el feed por `rel_next` con corte por fecha
(`date_field`, ventana `[desde, hasta]`, marca de agua incremental con
`desde=auto`) y aplana cada entrada con un `field_map` de rutas por nombre
local. El perfil **PLACSP CODICE** fija ese mapa, que incluye el **bloque de
adjudicación completo** (`TenderResult`): `resultado`, `fecha_adjudicacion`,
`adjudicatario`, `nif_adjudicatario`, `num_ofertas`, `importe_adjudicacion`.
No hacen falta recursos distintos para "adjudicaciones": cada cambio de estado
del expediente es una nueva entrada del mismo feed, y cuando el expediente
llega a adjudicado/resuelto la entrada trae ese bloque. Una vista de
adjudicaciones = filtrar por `estado` (ADJ/RES) o `resultado` no nulo.

### 2.2 ZIPs (históricos anuales)

Los repositorios históricos (anuales/mensuales de PLACSP) son ZIPs cuyos
ficheros internos son los mismos XML Atom del feed, archivados por lotes. Dos
caminos en el `AtomFetcher`:

- **Ejecución completa**: se descarga el ZIP entero **a memoria** (no a disco),
  se valida la firma `PK` (si no aparece suele ser el WAF devolviendo HTML por
  falta de `User-Agent`), y se procesan los miembros uno a uno (descomprimir →
  parsear → filtrar por ventana → acumular). Corpus cerrado: sin paginación ni
  frontera de parada.
- **Preview** (`_preview_limit`): lector **en streaming** que parsea las
  cabeceras locales (`PK\x03\x04`) según llegan los bytes, descomprime miembro
  a miembro y **corta la conexión** al alcanzar el límite — el resto del ZIP
  (cientos de MB) nunca viaja. Posible porque el ZIP coloca cada miembro tras
  su cabecera con tamaños (sin data descriptor en PLACSP), sin necesitar el
  índice central del final. El anual de 2022 pasó de 504 en el gateway a 100
  registros en ~14 s.

Los recursos históricos no piden fechas en runtime: el año del ZIP ya acota el
corpus; una subventana se fija editando los params del recurso.

## 3. La especie REST y sus categorías de variación

La familia REST es **una sola especie** (`RESTFetcher`) con tres ejes
ortogonales, cada uno un registro de estrategias con nombre:

- **Petición** (`request`): `query` | `json_body` | `form`. Con cuerpo, la
  plantilla (`payload_template`) admite el marcador `{pivot}`.
- **Paginación** (`pagination`): `none` | `query_offset` | `page_number` |
  `rel_next` | `cursor` | `pivot_loop`. `pivot_loop` no es paginación en
  sentido estricto pero es el mismo eje ("cómo se recorre"): una petición por
  valor de una lista.
- **Extracción** (`extraction`): ver §4.

Reglas de `pivot_loop` que conviene conocer (fidelidad con el histórico
`RestLoopFetcher`, absorbido en la fusión):

- `pivot_values` es canónicamente un **JSON array** (se tolera CSV). Sin
  `pivot_values`, error claro — nada de defaults silenciosos (el default
  histórico de 52 provincias INE se materializó en los seeds de los recursos
  que dependían de él, p. ej. Notarías).
- Con petición por cuerpo, el pivote viaja **solo** en el payload (no se filtra
  a la query). Con `request=query`, viaja como parámetro (`pivot_param`).
- `pivot_field_out`: anota en cada fila el valor del pivote que la produjo —
  esencial cuando la respuesta no lo repite (p. ej. el puente DIR3).
- Respuesta-objeto por pivote (un dict por petición, sin `content_field`)
  cuenta como un registro; los 204 se omiten.
- Dedup por `id_field` entre iteraciones del pivote.
- **Pivotes desde el almacén**: `pivot_source_odmgr_query` +
  `pivot_source_field` toman los valores de un dataset ya cosechado (lector
  común en `app/fetchers/pivot_sources.py`, compartido con HTMLFetcher).

## 4. Extracción: norma general

**Las estrategias de extracción no descartan información.** `passthrough`
entrega los registros tal cual; `tree_flatten` aplana respuestas jerárquicas
(nodos con hijos) en una fila por nodo conservando **todos** los campos propios
más la jerarquía (`nivel`, `padre_id`, `padre_descripcion`, `ruta`);
`const_fields` añade a cada fila campos constantes de contexto del recurso
(p. ej. `tipo_admon` en los órganos BDNS, que el endpoint no repite por nodo).
La excepción consciente es `field_map` (PLACSP), que selecciona porque el
CODICE completo es enorme; el XML crudo se excluye del staging
(`raw_xml_content`).

Caso BDNS órganos: el endpoint `/organos` solo expone `id`, `descripcion` y
`children` (verificado contra el API vivo y la spec archivada en
`docs/fuentes/bdns/`); lo que se perdía era el árbol. Con `tree_flatten`, el
ámbito estatal pasa de 22 registros raíz a 355 órganos con jerarquía.

## 5. El JSONL final y la "foto más reciente"

El staging acumula **todas** las instantáneas que el fetcher emite. Cuando la
fuente publica el mismo objeto varias veces (PLACSP: una entrada por cambio de
estado del expediente), el recurso puede declarar:

- `dedup_key` — campo clave (p. ej. `expediente`)
- `dedup_order_field` — campo de orden, default `fecha`

y el manager hace una post-pasada al cerrar el stream: el JSONL final conserva
**una fila por clave, la de orden mayor** (a igualdad o sin orden, la última
emitida; las filas sin clave se conservan). Implementación en dos lecturas por
offsets de byte — no carga el fichero en RAM, apto para los anuales.

Matiz importante: el dedup es **por ejecución** (cada ejecución produce su
dataset versionado). Si se cruzan datasets distintos (histórico 2022 ×
novedades), un expediente puede aparecer en ambos; el criterio del consumidor
sigue siendo quedarse con la `fecha` mayor.

## 6. Recursos que usan otros recursos

Cuatro mecanismos, de menos a más acoplado:

1. **`pivot_source_odmgr_query`** — un recurso itera los valores de un campo de
   un dataset de otro (§3). Ej.: el puente DIR3 itera los códigos del catálogo
   DIR3 contra `/organos/codigo` de BDNS.
2. **`DerivedDatasetConfig`** — catálogos como subproducto de la ejecución de
   un recurso (upsert por clave natural; p. ej. beneficiarios desde
   concesiones).
3. **`parent_resource_id`** — recursos hijos promovidos por el crawler Web Tree
   (modo discover → promover → hijo en modo stream).
4. **Especie `CruceDatasets`** (`CrossDatasetFetcher`) — el cruce declarativo
   de dos datasets, formalizado en §7.

## 7. Recursos derivados: la especie CruceDatasets

Un recurso cuyo "transporte" es el propio almacén de ODM. Declarativo y, por
ser un recurso normal, hereda gratis schedule, ejecuciones, salud, versionado
y linaje. Diseño original y estado en `docs/PENDIENTE_recursos_derivados.md`.

**Direccionamiento por recurso, no por query.** Las fuentes se referencian por
**nombre de recurso** (`left_resource`/`right_resource`; string o lista — con
varios se concatena la unión de sus datasets). El nombre de query se deriva en
runtime con `dataset_query_name`, así que sobrevive a regeneraciones del
dataset. `left_query`/`right_query` existen como vía avanzada, explícitamente
sin linaje.

**Semántica del cruce** (núcleo puro `cruzar`, testeable):
`left_key`/`right_key`; `match` = `eq` | `in_array` (la clave derecha es una
lista que contiene a la izquierda); `join` = `enrich` (todas las filas
izquierdas, las emparejadas suman campos del derecho) | `inner` (solo
emparejadas); `select` = mapa `{salida: campo_del_derecho}` (vacío: todos los
`right_fields` menos la clave). A igualdad de clave gana la última fila del
derecho — los datasets llegan ya deduplicados (§5).

**Linaje a máquina.** Tabla `opendata.resource_dependency`
(derivado → fuente, rol `left`/`right`, FK CASCADE). El fetcher resuelve los
ids de los recursos fuente y el manager sincroniza la tabla en cada ejecución
del derivado (idempotente: refleja las dependencias reales de la última
ejecución). Es la base de la señal pendiente "fuente más nueva que derivado",
que con esta tabla es una comparación trivial de fechas de último dataset.

**Frescura v1 por cron**: el derivado se programa después de sus fuentes.

## 8. El caso completo: subvenciones ↔ DIR3 ↔ licitaciones

DIR3 es la espina dorsal del cruce entre contratación y subvenciones:

| Pieza | Clave | Estado |
|---|---|---|
| Catálogo DIR3 | código DIR3 | cosechado (FileDownload) |
| PLACSP licitaciones | DIR3 nativo en el CODICE | en el field_map del perfil |
| BDNS órganos | id interno + jerarquía (`tree_flatten`) | cosechado |
| **Puente DIR3↔BDNS** | `pivot_loop` del catálogo DIR3 contra `/organos/codigo` → `{dir3, tipoAdmon, ids}` | `manifests/bdns_puente_dir3.json` |
| **Órganos con DIR3** | CruceDatasets: órganos (4 ámbitos, unión) × puente, `match=in_array`, `join=enrich` | `manifests/bdns_organos.json` (derivado) |

BDNS no expone el DIR3 en sentido directo (ni en `/organos` ni en el detalle
de convocatorias — verificado); `/organos/codigo?codigo=<DIR3>` resuelve el
sentido inverso, y con el catálogo DIR3 como fuente de pivotes el puente sale
como un recurso más. El último eslabón (convocatorias por órgano ×
licitaciones por DIR3) queda declarable con la misma especie cuando se
cosechen convocatorias por órgano.

## 9. Referencias

- `docs/PENDIENTE_recursos_derivados.md` — diseño y estado del cruce.
- `docs/fuentes/placsp.md`, `docs/fuentes/bdns/` — fichas de fuente y specs.
- `docs/versionado_datasets.md`, `docs/diseno_ciclo_vida_datasets.md` —
  versionado y ciclo de vida.
- `docs/manual_usuario.md` — operación desde la UI.
