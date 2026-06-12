# Entrega delta (changeset) por versión de dataset

Mecanismo **opt-in** para que ODM ofrezca a un suscriptor solo las **novedades**
entre dos versiones consecutivas de un dataset, en lugar del dataset completo.

> Estado: **propuesta de diseño**. No implementado. Documento de fijación previo
> a la implementación.

## Dos ejes distintos, no confundir

ODM tiene dos puntos donde se puede ahorrar trabajo, y son ortogonales:

| Eje | Quién→quién | Pieza | Estado |
|---|---|---|---|
| **Captación incremental** | fuente → ODM | `app/services/incremental.py` (`incremental_field` / `incremental_param`) | implementado, opt-in |
| **Entrega delta** | ODM → suscriptor | este documento (`changes.jsonl` + `delivery_mode`) | propuesta |

La captación incremental reduce lo que ODM **pide** al portal origen inyectando
un "desde" (watermark). La entrega delta reduce lo que ODM **envía** al
consumidor. Componen bien (ver §Sinergia) pero son independientes: un recurso
puede tener una sin la otra.

## Motivación: el caso BDNS

La Base de Datos Nacional de Subvenciones es el caso canónico:

- **Base histórica enorme**: cientos de miles de convocatorias y concesiones.
- **Append-mostly**: cada ciclo añade registros nuevos; los antiguos casi nunca
  mutan.
- **Identidad estable**: cada convocatoria tiene su código BDNS; cada concesión,
  su identificador. Hay clave primaria natural.

Reenviar el dataset completo en cada notificación cuando el 99 % es idéntico
desperdicia descarga, proceso y republicación en el consumidor. El delta convierte
ese ciclo en "estas N altas + M modificaciones + K bajas".

## Condiciones duras (sin ellas un delta no está definido)

1. **Clave de registro estable.** Sin clave primaria por fila no se puede decir
   qué fila es nueva, cuál cambió y cuál desapareció; solo cabría un diff a nivel
   de blob ("cambió: sí/no"), que no aporta. Donde no haya clave fiable, el
   recurso no es delta-capaz y se entrega siempre completo.
2. **Cambio de esquema ⇒ full.** Un delta fila-a-fila contra la versión previa
   es ambiguo si entre medias cambió el esquema. Se reutiliza
   `app/utils/versioning.py::compute_schema_diff`: si hay diff de esquema (versión
   `major`), se fuerza entrega completa, nunca delta.
3. **Detección de hueco + fallback a snapshot.** Los deltas derivan: si el
   consumidor se pierde una entrega y aplica el siguiente delta sobre una base
   obsoleta, corrompe en silencio. Por eso **ODM nunca deja de producir el
   snapshot completo versionado** (la línea base auto-sanante). El delta es una
   capa encima, no un reemplazo.

## Neutralidad

ODM sigue siendo productor neutro. El changeset (altas/modificaciones/bajas + clave
+ secuencia de versión) es un artefacto **neutro**: no asume CKAN ni la semántica
de aplicación de ningún consumidor. *Cómo* se aplica el delta (upsert/delete en
CKAN DataStore, regeneración de fichero, etc.) es responsabilidad exclusiva del
consumidor y no entra en ODM.

## Declaración (patrón operador-declarado, como el fetch incremental)

Igual que `incremental_field`/`incremental_param`, la clave la declara el
**operador** mediante `ResourceParam`, porque solo él sabe qué identifica un
registro en esa fuente. No se infiere por fuente.

| Param | Significado |
|---|---|
| `record_key` | campo(s) que identifican unívocamente una fila (p. ej. `codigo_bdns`, o compuesta `numeroConvocatoria,beneficiario`) |

Sin `record_key`, el recurso no es delta-capaz: entrega completa siempre.

## Cómputo del changeset

En el pipeline de construcción de dataset (tras materializar la versión `N`),
si el recurso declara `record_key` y existe la versión `N-1` materializada:

1. `compute_schema_diff(N-1, N)` → si hay rotura de esquema, **se omite el
   changeset** (entrega full, versión `major`).
2. Diff por clave entre `N-1` y `N`:
   - claves en `N` y no en `N-1` → `add`
   - claves en ambas con hash de fila distinto → `mod`
   - claves en `N-1` y no en `N` → `del`
3. Se materializa el artefacto **`changes.jsonl`** junto a `data.jsonl`. Cada
   línea: `{"op": "add|mod|del", "key": <valor clave>, "row": {…}}` (`row` se
   omite en `del`). Cabecera/metadata del artefacto: `base_version` (= `N-1`),
   `target_version` (= `N`), `record_key`.

El snapshot completo (`data.jsonl`) se sigue produciendo siempre.

## Suscripción: preferencia de entrega

Nueva preferencia en `ResourceSubscription`, hermana de `auto_upgrade` y
`pinned_version` (vive en ODM, coherente con la frontera "soy suscriptor = ODM"):

| Campo | Valores | Por defecto |
|---|---|---|
| `delivery_mode` | `full` \| `delta` | `full` |

`delta` solo surte efecto si el dataset es delta-capaz para esa versión (hay
`record_key` y existe changeset). En cualquier otro caso se degrada a `full` de
forma transparente.

## Payload del webhook

El webhook firmado (HMAC-SHA256, `X-ODM-Signature`) que arma
`notification_service.py` gana campos **opcionales** cuando aplica entrega delta:

- `delivery: "delta"` (vs el `full` actual implícito)
- `changes_url`: URL de `changes.jsonl`
- `base_version`: versión sobre la que se aplica el delta

Cuando no aplica delta, el payload es el actual (con `download_urls` al snapshot).
El bloque graphql (`_build_graphql_payload`) tendría su equivalente: una query de
delta parametrizada por `base_version`.

## Seguridad de aplicación (lado consumidor, informativo)

El consumidor compara su `published_version` con `base_version` del payload:

- coinciden → aplica el delta;
- no coinciden (hueco) → **ignora el delta y descarga el snapshot completo**
  (`download_urls` del último), reconciliando.

Un `major` (rotura de esquema) llega siempre como `full`. Así el consumidor nunca
acumula deriva silenciosa.

## Acoplamiento con retención

Para diferenciar `N` contra `N-1`, las filas materializadas de `N-1` deben seguir
retenidas (`DatasetLease` / `plazo_concedible`). Si la política de retención
desaloja la versión base, ODM no puede computar el changeset → anuncia solo
`full` para esa entrega. La capacidad delta y la retención quedan acopladas: un
dataset que quiera entrega delta fiable necesita retener al menos `N-1`.

## Sinergia con captación incremental

Cuando un recurso ya capta incremental (`incremental_param`), la ejecución trae
del origen sobre todo filas nuevas, de modo que el changeset contra `N-1` es
barato (mayoritariamente `add`). Son dos opt-in que se refuerzan, pero la entrega
delta funciona también sobre recursos de full pull, porque el diff se hace contra
la versión previa materializada, no contra lo captado.

## Cuándo NO conviene

- **Datasets pequeños**: el snapshot ya es barato; el delta añade complejidad sin
  retorno. Umbral de tamaño por debajo del cual ni se computa changeset.
- **Sin clave estable**: indefinido, se entrega full.
- **Cambio de esquema**: full por definición.

## Beneficio colateral

Exigir `record_key` por dataset fija la **identidad de registro**, que es justo lo
que también hace bueno el publicado en CKAN DataStore (upsert/delete por PK). No es
solo optimización de transporte: profesionaliza el consumo incremental aguas abajo.

## Plan de implementación (orden)

1. `record_key` como `ResourceParam` reconocido + validación de unicidad en la
   versión actual.
2. Cómputo de changeset en el builder (tras materializar la versión), gateado por
   `record_key` + `compute_schema_diff` + umbral de tamaño; materializa
   `changes.jsonl`.
3. `delivery_mode` en `ResourceSubscription` + migración `IF NOT EXISTS`.
4. Campos opcionales en el payload de `notification_service.py` (+ equivalente
   graphql).
5. Lado consumidor (ckan-jerez, fuera de ODM): aplicación delta con upsert/delete
   en DataStore y fallback a snapshot por hueco de versión.
