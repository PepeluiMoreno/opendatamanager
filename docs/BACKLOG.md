# Backlog

Tareas ejecutables de forma autónoma: bugs, verificaciones y mejoras puntuales
(normalmente nacidas de revisar el UI mientras se madura la siguiente propuesta
de calado). Lo arquitectónico NO va aquí: va a `DECISIONES_pendientes.md` y se
decide antes de construir.

Convención: `[ ]` pendiente · `[x]` hecho (con commit) · `[-]` descartado (con motivo).

## Pendiente

- [ ] **Web Tree — scoping del crawler** (verificado en vivo contra Jerez): el
  crawler no puede acotarse a una rama; arrancando en /economica/deuda
  descubrió 708 hojas del portal entero (el menú global enlaza a todo). El
  brief original (chat.md) ya preveía include_patterns/exclude_patterns; la
  implementación mergeada los omitió. Reponerlos como params del WebTreeFetcher
  (filtrar páginas a seguir y/o URLs hoja a conservar por patrón de path).

- [x] **Arnés batch de pruebas de recursos** (este push): script paralelo con
  clasificación OK/SIN FILAS/FUENTE CAÍDA/CONFIG ROTA/BUG y sello de
  last_tested_at. Primera pasada completa sobre los 42 activos:
  docs/INFORME_arnes_2026-06-07.md (34 OK).
- [x] **Fuentes DIR3**: el ítem estaba desfasado — el CSV FUNCIONA (126.368
  filas), solo era lento; timeout 240 fijado en seed. Cabecera pendiente de
  verificar quedaba cubierta: el fetch produce las columnas esperadas.
- [x] **Catastro Sevilla — eje del bbox**: el WFS INSPIRE exige lat,lon;
  corregido en seed (verificado en vivo con bbox pequeño).

- [ ] **Hacienda - PMP Entidades Locales**: 404; localizar la URL vigente en
  serviciostelematicosext.hacienda.gob.es (CONPREL).
- [ ] **Registros de la Propiedad (CORPME)**: 404; el documento de
  registradores.org cambió de ruta.
- [ ] **Jerez ×3 (Deuda/Morosidad/PMP)**: el portal cambió las rutas `{year}`;
  localizar el patrón nuevo en transparencia.jerez.es.
- [ ] **Catastro Sevilla — troceo**: la petición provincia-entera (count=500)
  tumba el WFS (500 tras 233s); trocear por municipios o rejilla de bboxes.
- [ ] **Geonames ES.zip**: 503 persistente hoy (throttling); reintentar y, si
  persiste, mirror alternativo.

- [x] **Sección 'Fuera del catálogo' vaciada de raíz** (este push): esas
  claves eran parámetros que las variantes usan pero la especie NO declaraba
  (¡incluidos start_param/page_size_param que lee la propia paginación!). Se
  completan las definiciones de API REST (+4: start_param, page_size_param,
  delay, id_field) y Feeds ATOM/RSS (+4: timeout, max_pages, dedup_key,
  dedup_order_field), con hint y condición. Las variantes vuelven a fijar
  valores 100% sobre el vocabulario de su especie; la sección queda como red
  de seguridad que no debería verse nunca.

- [x] **Despliegue progresivo en la creación del recurso** (este push): el
  árbol de decisiones arranca en la variante — la visibilidad de cada
  parámetro se evalúa contra el valor EFECTIVO (override del recurso →
  variante → default), así que elegir CKAN despliega solo los parámetros de
  sus decisiones. Fuera del formulario del recurso toda anotación de
  mecánica ('[heredado del perfil: …]', placeholders de herencia); el
  selector pasa a llamarse 'Variante'.

- [x] **Hints en todos los parámetros** (commit en este push): cada parámetro
  del catálogo lleva un hint que explica qué es y qué valores suele tener —
  184/184, incluidos los 24 que faltaban (urls de especies aspiracionales,
  broker MQTT, bootstrap de Kafka, page_param del HTML genérico...).

- [ ] **deploy-healthcheck.patch** sobre `.github/workflows/deploy.yml`: debe
  aplicarse desde el editor web de GitHub (el PAT en uso no tiene scope
  `workflow`). Sin él, los workflows salen verdes aunque el contenedor no
  levante.
- [ ] **En prod tras los últimos deploys**: ejecutar `python seed_resources.py`
  (FACE, JdA, CEE, datos.gob.es, INE, retirada del scraper de provincia).
- [ ] **Rotar el PAT** del repositorio al cerrar la racha de trabajo actual.
- [ ] **RER vía Power BI**: falta capturar el `query_json` real
  (`config_rer.md`).

## Hecho

(se irá rellenando con commit asociado)
