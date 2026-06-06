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
**Evidencia acumulada**: segunda víctima (2026-06): la migración de
resource_candidate abría con un DROP TABLE 'de limpieza' que, re-ejecutado en
cada boot, vaciaba TODAS las candidatas en cada redeploy — dejando huérfanos a
los recursos hijos del Web Tree en prod (Test y Run rotos). Una migración
normal solo se ejecuta una vez y aquel DROP habría sido inocuo.
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

### 7. Jerez: ¿sustituir los 3 recursos rotos por candidatos Web Tree?
**Contexto**: Deuda anual, PMP mensual y morosidad trimestral fallaron en el
arnés (PDF_TABLE con URLs {year} que el portal cambió). El reconocimiento
Web Tree los reinfiere solos como candidatos con dimensiones correctas
(DeudaFinanciera-31-12-{year}.pdf [year]; Informe_PMP_{year}_{month}.xlsx
[year,month]; Informe_Ta_Ley_15.10-{year}-{quarter}oT.pdf [year,quarter]).
**Opciones**: (a) arreglar a mano las URLs de los 3 recursos PDF_TABLE
(rápido, pero frágil: el portal volverá a moverlas); (b) sembrar un crawler
Web Tree de la rama c-deuda, promover los 3 candidatos y retirar los recursos
manuales (robusto y mejor modelado, pero requiere antes el scoping del crawler
—ver BACKLOG— para no descubrir el portal entero).
**Recomendación**: (b), después del scoping. Es el primer caso de uso real del
Web Tree y cierra 3 ítems del backlog con el mecanismo correcto.
**Estado**: sin decidir.

---

## Decididas (histórico breve)

- **2026-06-07 — Candado selectivo (§6, opción c)**: la variante puede marcar
  parámetros como inviolables (no pisables por el recurso ni por la
  ejecución); el resto siguen siendo defaults pisables con gesto deliberado.
  Estreno: field_map de PLACSP CODICE. Doctrina: *ajustes pisables, esencias
  con candado*. Implementación: fetcher_preset.locked_params, factory,
  GraphQL, seed y UI (toggle 🔒 en el editor de la variante, chip '🔒 fijo'
  sin Sobrescribir en el recurso).

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
