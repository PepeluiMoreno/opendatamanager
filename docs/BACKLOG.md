# Backlog

Tareas ejecutables de forma autónoma: bugs, verificaciones y mejoras puntuales
(normalmente nacidas de revisar el UI mientras se madura la siguiente propuesta
de calado). Lo arquitectónico NO va aquí: va a `DECISIONES_pendientes.md` y se
decide antes de construir.

Convención: `[ ]` pendiente · `[x]` hecho (con commit) · `[-]` descartado (con motivo).

## Pendiente

- [x] **Jerez — recursos Web Tree creados** (este push): scripts/jerez_webtree.py
  hace el ciclo completo (crawler padre acotado a a07-economica → discover →
  infer → persiste candidatas → promueve). Ejecutado: 3.129 hojas → 64 recursos
  (35 series + 29 bundles). Stream verificado end-to-end (descarga + columna de
  dimensión + procedencia). PENDIENTE en prod: ejecutar el script allí (crea los
  recursos en su BD).
- [ ] **Web Tree — calidad de parseo en bundles de PDF heterogéneos**: las
  series XLSX (PMP, deuda) parsean limpio; los bundles de PDFs de resoluciones
  no son tabulares y el parser genérico saca filas pobres. Decidir si esos
  bundles se tratan como 'registro documental' (lista de URLs + metadatos) en
  vez de intentar extraer tabla.

- [x] **Web Tree — scoping del crawler** (este push): repuestos path_prefix
  (acota la navegación a una subrama) e include/exclude_patterns (filtran las
  hojas por regex). Verificado en Jerez: de 708 hojas del portal entero a 282
  de c-deuda, candidatos limpios.
- [x] **Web Tree — inferer que funciona en portales documentales** (este push):
  dos pasadas nuevas tras el templating — (1) consolidación: colapsa plantillas
  hermanas que difieren en un átomo genérico (números de resolución, nombres de
  mes embebidos) en una dimensión {code}; (2) serie-vs-pila: una serie periódica
  (mes/trimestre) o de carpeta pequeña se conserva suelta, y una carpeta-
  vertedero (muchas series o documentos heterogéneos) colapsa en un bundle
  {*} por carpeta. Verificado en Jerez: deuda 282→11 propuestas, presupuesto
  1745→16, cuenta general 818→1. Antes: ~1.595.

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
