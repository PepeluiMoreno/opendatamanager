# Decisiones pendientes

Propuestas de calado (diseño, refactors, arquitectura) que se **anotan y se
deciden juntos antes de construir**. Cada entrada: contexto, opciones y
recomendación. Lo ya decidido se mueve a su registro definitivo
(`arquitectura_datos.md` o el documento que corresponda) con fecha.

Las tareas ejecutables sin deliberación van a `BACKLOG.md`.

---

## En deliberación

### 1. Implementación del ciclo de vida de datasets
**Contexto**: diseño consolidado en `diseno_ciclo_vida_datasets.md` (caché
provisionada, leases, re-derivabilidad), sin implementar. Los datasets crecen
sin purga (~7 GB/5 años solo PLACSP).
**Opciones**: (a) implementar el diseño completo; (b) empezar solo por la purga
con suelo de política (sin leases); (c) seguir esperando a que duela más.
**Recomendación**: (b) — la purga simple captura la mayor parte del valor con
una fracción del coste; los leases cuando haya consumidores reales.
**Estado**: sin decidir.

### 2. El `DROP` de `alembic_version` en el entrypoint
**Contexto**: el arranque borra la tabla de versiones de Alembic, forzando que
TODAS las migraciones se re-ejecuten en cada boot y deban ser idempotentes a
mano (SQL crudo con `IF NOT EXISTS`). Ya causó un crash-loop (migración no
idempotente) y es una trampa permanente para migraciones futuras.
**Opciones**: (a) dejar de borrarla y confiar en el versionado normal de
Alembic; (b) mantener el borrado y el patrón idempotente como doctrina de la
casa (está documentado en cada migración).
**Recomendación**: (a) a medio plazo; exige verificar que el historial de
revisiones de prod está sano antes de cambiarlo.
**Estado**: sin decidir.

### 3. Criterio de permanencia de las variantes (en observación)
**Contexto**: registrado en `arquitectura_datos.md` §5b. Con CKAN/DKAN/ODS/
Socrata + las tres semánticas REST heredadas + PLACSP CODICE hay 8 variantes en
2 especies: el criterio se va cumpliendo.
**Estado**: en observación hasta que el parque de recursos se estabilice
(tras pasar el arnés batch); entonces se ratifica o se pliega a manifiestos.

### 5. Renombrado de código: preset → variant
**Contexto**: la terminología de usuario es ya 'variante' en todo el proyecto
(UI, descripciones, docs), pero el código conserva FetcherPreset, preset_id,
presetId (GraphQL) y la clave 'preset' en los manifiestos.
**Opciones**: (a) dejar el código como está (la entidad interna no se ve);
(b) renombrado completo: tabla+columna (migración), tipos y mutaciones GraphQL
(rompe clientes), clave de manifiesto con alias retrocompatible.
**Recomendación**: (a) mientras el API GraphQL no tenga más consumidores que
el frontend propio; si se hace (b), aprovechar una ventana de cambios
rompientes y hacerlo entero de una vez.
**Estado**: sin decidir.

---

## Decididas (histórico breve)

- **2026-06-07 — Árbol de decisiones en la definición: anidamiento por
  controlador (opción b)**: dentro de cada grupo, los parámetros condicionales
  cuelgan como ramas bajo su controlador, etiquetadas con el valor que las
  activa; el chip textual 'solo con…' desaparece, sustituido por estructura.

- **2026-06-06 — Los joins no viven en la plataforma** (opción B): ODM produce
  piezas, incluidas las piezas-conector; el ensamblaje es del consumidor.
  Detalle en `PENDIENTE_recursos_derivados.md` y `arquitectura_datos.md` §7.
- **2026-06-06 — Multi-fetcher descartado**: única resurrección legítima
  escrita (composición de transporte de UNA fuente, nunca analítica).
- **2026-06-07 — Variantes como implementaciones concretas de la especie**:
  un único juego de parámetros fundido en el UI; las semánticas REST
  heredadas (Paginada, Loop de pivotes, Series temporales) son variantes.
