# Auditoría, identidad de recursos y cuota de refrescos

Tres mecanismos relacionados pero **independientes** introducidos sobre el modelo
de recursos de ODM.

## 1. Auditoría: `AuditMixin` en todos los modelos

Todos los modelos de dominio (`app/models.py`) heredan de `AuditMixin`, que aporta
cuatro columnas uniformes:

| columna         | significado                                  |
|-----------------|----------------------------------------------|
| `created_at`    | fecha de creación (default al insertar)      |
| `updated_at`    | fecha de última modificación (onupdate)      |
| `created_by_id` | usuario/aplicación que creó la fila (FK)     |
| `updated_by_id` | usuario/aplicación que la modificó (FK)      |

`created_by_id`/`updated_by_id` referencian `opendata.usuario.id`. Para una
aplicación, el principal es su **usuario funcional** (`svr-ckan-jerez`, `svr-sipi`…),
es decir: *usuario = aplicación*.

### Estampado automático en cada transacción

No hay que rellenar estos campos en cada mutation. Un listener `before_flush`
(`app/audit.py`) los estampa en **toda** transacción:

- el contexto GraphQL (`get_graphql_context` en `main.py`) fija el principal de la
  petición con `set_usuario_actual(usuario.id)`;
- el listener recorre `session.new` (rellena `created_by_id`/`updated_by_id`) y
  `session.dirty` (actualiza `updated_by_id`) de cualquier instancia `AuditMixin`.

`created_at`/`updated_at` los gestiona el propio mixin (default / onupdate).

## 2. Identidad de un recurso: la huella (`params_hash`)

El `name` de un `Resource` es una etiqueta humana, **no** su identidad. Dos apps
pueden pedir la misma fuente con nombres distintos. La identidad real es *qué trae*:
el conjunto de pares `(clave, valor)` de sus `params`.

`Resource.params_hash` = SHA-256 de la forma canónica de `params` (pares ordenados
por clave, valores como string, JSON compacto; ver `app/core/huella.py`). Se
prescinde de `name` y de los campos operativos (`schedule`, `active`, `target_table`,
`description`), que **no** son params. Para params externos (`is_external`), el
`value` debe ser la *referencia* al secreto, nunca el secreto resuelto.

> Es distinto de `Resource.manifest_hash` (hash del manifiesto canónico completo,
> usado para versionado/detección de conflictos). La huella es para *identidad*.

### `create_resource` se vuelve idempotente (ensure)

Al crear un recurso se calcula su huella:

- si ya existe un recurso (no borrado) con esa huella → **no se duplica**: se
  devuelve el existente y el solicitante queda como *suscriptor*;
- si la huella es nueva → se crea y el solicitante queda como **dueño**
  (`created_by_id`).

`update_resource` recalcula la huella si cambian los `params` y **rechaza** el
cambio si colisiona con otro recurso (editar la identidad crearía un duplicado:
hay que crear uno nuevo o suscribirse al existente).

La unicidad se garantiza con la constraint `uq_resource_params_hash`. El backfill de
la migración calcula la huella de los recursos existentes (dedup *first-wins*).

## 3. Propiedad y autoridad sobre el `schedule`

El **dueño** de un recurso es quien lo creó (`created_by_id`). Solo el dueño puede
cambiar su `schedule` de refresco (`update_resource` lo verifica). Los demás
**consumen** la cadencia establecida o piden un refresco a demanda (con cuota).

## 4. Cuota de refrescos a demanda

- El refresco **programado** (scheduler) ejecuta `FetcherManager` directamente: no
  pasa por la mutation, **no consume cuota** y beneficia a todos los suscriptores.
- El refresco **a demanda** (`executeResource`) consume la cuota del solicitante.

`Usuario.cuota_refrescos_diaria` (default **50**, `0` = sin refrescos extemporáneos)
limita los refrescos a demanda por usuario y día. Cada refresco a demanda se
registra en `refresco_extemporaneo` (ledger: auditoría + contador). `executeResource`
cuenta los del día para el principal y, si alcanza la cuota, lo rechaza con un mensaje
claro en vez de ejecutar.

> Nota: un refresco a demanda de A deja el dataset fresco para B *gratis*. Es
> correcto cobrar a quien dispara el trabajo, no a quien lo aprovecha.

## Migración

`alembic/versions/20260608_1200-a2b3c4d5e6f8_auditoria_huella_cuota.py`:
columnas de auditoría en todas las tablas de dominio, `params_hash` + backfill +
constraint única, `cuota_refrescos_diaria`, y la tabla `refresco_extemporaneo`.
