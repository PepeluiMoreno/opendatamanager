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

### 4. Visualizar el árbol de decisiones en la definición de la especie
**Contexto**: en el recurso, los parámetros se despliegan según las decisiones
(variante → ejes → dependientes) y no hace falta explicar nada. En la
DEFINICIÓN de la especie ocurre lo contrario: hay que ver el árbol completo de
golpe, y hoy se aproxima con grupos colapsables y el chip 'solo con
pagination = …' — que funciona pero es texto, no estructura.
**Opciones**:
  (a) *Status quo*: grupos + chip de condición. Coste cero, legibilidad media.
  (b) *Anidamiento por controlador*: dentro de cada grupo, los parámetros
  condicionales se indentan bajo su parámetro controlador, agrupados por el
  valor que los activa (pagination ▸ cursor ▸ cursor_param, next_cursor_field…).
  El árbol se VE como árbol. Coste moderado, solo presentación.
  (c) *Simulador*: un modo 'probar' en la ficha que reusa el motor del
  formulario del recurso — eliges valores de eje y ves el juego resultante.
  Fiel pero no muestra el árbol entero de un vistazo.
  (d) *Diagrama* (grafo). Coste alto, probablemente sobreingeniería.
**Recomendación**: (b), opcionalmente complementada con (c) más adelante; (b)
convierte la condicionalidad en estructura visual sin tocar el modelo.
**Estado**: sin decidir.

---

## Decididas (histórico breve)

- **2026-06-06 — Los joins no viven en la plataforma** (opción B): ODM produce
  piezas, incluidas las piezas-conector; el ensamblaje es del consumidor.
  Detalle en `PENDIENTE_recursos_derivados.md` y `arquitectura_datos.md` §7.
- **2026-06-06 — Multi-fetcher descartado**: única resurrección legítima
  escrita (composición de transporte de UNA fuente, nunca analítica).
- **2026-06-07 — Variantes como implementaciones concretas de la especie**:
  un único juego de parámetros fundido en el UI; las semánticas REST
  heredadas (Paginada, Loop de pivotes, Series temporales) son variantes.
