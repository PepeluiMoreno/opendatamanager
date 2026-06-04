# Fetch incremental y cortesía por publisher

Dos mecanismos para no maltratar los portales fuente y reducir el coste de cada
ejecución.

## Cortesía (implementado)

- **Backoff de 429/503 con `Retry-After`** en `app/fetchers/base.py::_request`:
  un límite de tasa transitorio ya no aborta la ejecución; se respeta el
  `Retry-After` del servidor (segundos o fecha HTTP) y, en su defecto, backoff
  exponencial.
- **Gating por publisher** en `app/services/scheduler_service.py`: intervalo
  mínimo entre arranques de recursos del mismo publisher
  (`ODM_PUBLISHER_MIN_INTERVAL_S`, 30 s por defecto), para no martillear un
  portal cuando varios cron coinciden.

## Fetch incremental (opt-in, `app/services/incremental.py`)

Cada ejecución es hoy un *full pull*. El soporte incremental es **opt-in por
recurso** y no fuerza comportamiento en fuentes que no lo soportan.

Un recurso lo activa declarando dos `ResourceParam`:

| Param | Significado |
|---|---|
| `incremental_field` | campo del dataset cuyo máximo es el watermark (p. ej. `fecha_alta`, `last_modified`, `id`) |
| `incremental_param` | nombre EXACTO del parámetro que la fuente entiende para "desde" (p. ej. `fechaDesde`, `since`) |

Antes de ejecutar, el manager calcula el watermark (máximo de `incremental_field`
en el último dataset) e inyecta `{incremental_param: watermark}` en los
`execution_params`. Los fetchers que entienden ese parámetro lo usan; el resto lo
ignoran. Si el recurso no declara `incremental_param`, se mantiene el full pull.

`incremental_param` lo declara el operador porque solo él sabe si la fuente
soporta consulta incremental: así no se inventa comportamiento por fuente.

### Punto de integración

`app/services/incremental.py::compute_watermark(session, resource)` devuelve el
watermark o `None`. La activación es una sola inyección en `FetcherManager.run`:
si `resource_incremental_config(resource)` no es `None`, añadir
`{cfg["param"]: compute_watermark(...)}` a los `execution_params` antes de
construir el fetcher. Queda pendiente de cablear y probar contra un recurso real
con campo de fecha (p. ej. BDNS Concesiones con `fechaDesde`).
