# Política de versionado de datasets

OpenDataManager trata cada dataset como una **dependencia versionada**. Cada
ejecución que produce datos genera una versión semántica `MAJOR.MINOR.PATCH`
comparando el esquema JSON nuevo con el de la versión anterior del mismo
recurso. La lógica vive en `app/utils/versioning.py` y se valida en
`tests/utils/test_versioning.py`.

## Reglas de incremento

El diff de esquema es **recursivo**: desciende en objetos anidados
(`properties`) y en los items de array (`items`), de modo que un cambio profundo
ya no se clasifica por error como `PATCH`.

| Cambio detectado | Resultado |
|---|---|
| Se elimina un campo (a cualquier profundidad) | **MAJOR** |
| Cambia el `type` de un campo | **MAJOR** |
| Cambia el `format` de un campo (p. ej. `date` → `date-time`) | **MAJOR** |
| Se estrecha un `enum` (se eliminan valores admitidos) | **MAJOR** |
| Un campo deja de ser `required` | **MAJOR** |
| Se añade un campo nuevo | **MINOR** |
| Se amplía un `enum` (se añaden valores) | **MINOR** |
| Un campo pasa a ser `required` (garantía más fuerte) | **MINOR** |
| Solo cambian los datos, no el esquema | **PATCH** |

Si concurren varios cambios, **manda el más alto** (cualquier cambio de rotura
hace la versión MAJOR; si no hay rotura pero sí cambios compatibles, MINOR; en
otro caso, PATCH).

## Suscripciones: `auto_upgrade` y `pinned_version`

Una `DatasetSubscription` controla qué versiones acepta una aplicación:

- **`auto_upgrade`** define el *techo* de incremento que la aplicación acepta
  automáticamente:

  | Política | Se auto-acepta (y notifica) |
  |---|---|
  | `patch` (por defecto) | solo PATCH |
  | `minor` | PATCH y MINOR |
  | `major` | todo |

- **`pinned_version`** fija a qué versiones se está suscrito. Formatos:
  `1.2.3` (exacta), `1.2.*` (cualquier patch de 1.2), `1.*` (cualquier minor de
  1) o `*`/vacío (cualquiera). **Una versión que no satisface el pin no se
  notifica**, con independencia de `auto_upgrade`.

### Alerta obligatoria en rotura (MAJOR)

Un cambio **MAJOR siempre se notifica** aunque la política `auto_upgrade` no lo
auto-acepte (salvo que el `pinned_version` lo excluya). El motivo: una rotura de
esquema requiere acción del consumidor y silenciarla sería peligroso. En ese
caso el payload incluye:

```json
"auto_upgrade": { "policy": "patch", "applies": false, "requires_action": true }
```

`applies: false` indica que la aplicación **no** debe auto-actualizarse;
`requires_action: true` señala que hay una rotura que atender manualmente.

## Limitaciones conocidas

- El diff compara estructura (`type`, `format`, `enum`, `required`,
  anidamiento). No interpreta semántica de negocio (p. ej. cambiar el
  significado de un código manteniendo el tipo se clasifica como PATCH).
- La clasificación de `format` como MAJOR es conservadora: cualquier cambio de
  `format` se considera potencialmente rompedor para el consumidor.
