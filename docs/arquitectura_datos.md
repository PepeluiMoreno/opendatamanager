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

## 5b. Variantes (perfiles): criterio de permanencia

Una variante es una implementación concreta de la tecnología de una especie:
fija valores sobre el vocabulario de parámetros de la especie, y los recursos
la eligen y heredan (sobrescribiendo campo a campo si hace falta). La entidad
está **en periodo de prueba** con criterio falsable: paga su peso si existen
varias variantes por especie con muchos recursos detrás; si el parque se
estabiliza con ≤1 variante por especie, se plegará a bloques compartidos de
manifiesto y se retirará.

Estado (2026-06-07): la dirección que la valida es tratar las **plataformas de
portales de datos como dialectos REST** — variantes CKAN, DKAN, OpenDataSoft y
Socrata bajo la especie API REST (cada una fija paginación, extracción e
id_field de su plataforma; el recurso solo aporta la URL del portal), todas
verificadas contra portales vivos. Junto a PLACSP CODICE bajo Feeds ATOM/RSS:
5 variantes en 2 especies.

## 6. Recursos que usan otros recursos

Tres mecanismos vivos, todos de transporte:

1. **`pivot_source_resource`** — un recurso itera los valores de un campo de
   un dataset de otro (§3). Ej.: el puente DIR3 itera los códigos del catálogo
   DIR3 contra `/organos/codigo` de BDNS.
2. **`DerivedDatasetConfig`** — catálogos como subproducto de la ejecución de
   un recurso (upsert por clave natural; p. ej. beneficiarios desde
   concesiones).
3. **`parent_resource_id`** — recursos hijos promovidos por el crawler Web Tree.

## 7. Dónde viven los joins: en el consumidor

Decisión de diseño (2026-06-06): **los joins no viven en la plataforma**. Un
cruce es una opinión sobre el uso (claves, normalización, huérfanos) y cada
consumidor puede necesitar una distinta; incrustarlo en ODM forzaba la
filosofía del fetcher (la especie `CruceDatasets`, retirada: origen interno,
publisher ficticio, gobernanza especial, auto-llamada HTTP).

La línea: *ODM produce piezas, incluidas las piezas-conector; el ensamblaje es
del consumidor.*

- **Puentes de identidad** = datos de referencia que ODM publica como recursos
  ordinarios. El que requiere resolución por denominación se produce con la
  herramienta de curación offline (`scripts/cruce_curacion.py`), que marca las
  ambigüedades para revisión humana — la resolución de identidad merece ojos.
- **Cruces analíticos** = aplicaciones consumidoras, con joins exactos sobre
  las piezas servidas por la API de datos.
- Frontera del multi-fetcher (descartado): solo se reabriría si una MISMA
  fuente exigiera dos llamadas para componer UN registro (composición de
  transporte, nunca analítica entre datasets).

## 8. El caso completo: subvenciones ↔ DIR3 ↔ licitaciones

DIR3 es la espina dorsal del cruce, que se materializa EN EL CONSUMIDOR:

| Pieza (servida por ODM) | Clave | Estado |
|---|---|---|
| Catálogo DIR3 | código DIR3 | fuentes 404 — pendiente reparar |
| PLACSP licitaciones | DIR3 nativo en el CODICE | en el field_map del perfil |
| BDNS órganos (jerarquía) | id interno | cosechado (`tree_flatten`) |
| **Puente DIR3↔BDNS** | batch anual contra `/organos/codigo` → `{dir3, tipoAdmon, ids}` | manifiesto listo, desactivado hasta reparar DIR3 |

Con esas piezas, `licitación.dir3 = puente.dir3` y `puente.ids ∋ órgano.id`
son joins exactos en la aplicación consumidora.

## 9. Referencias

- `docs/PENDIENTE_recursos_derivados.md` — diseño y estado del cruce.
- `docs/fuentes/placsp.md`, `docs/fuentes/bdns/` — fichas de fuente y specs.
- `docs/versionado_datasets.md`, `docs/diseno_ciclo_vida_datasets.md` —
  versionado y ciclo de vida.
- `docs/manual_usuario.md` — operación desde la UI.
