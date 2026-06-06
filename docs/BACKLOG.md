# Backlog

Tareas ejecutables de forma autónoma: bugs, verificaciones y mejoras puntuales
(normalmente nacidas de revisar el UI mientras se madura la siguiente propuesta
de calado). Lo arquitectónico NO va aquí: va a `DECISIONES_pendientes.md` y se
decide antes de construir.

Convención: `[ ]` pendiente · `[x]` hecho (con commit) · `[-]` descartado (con motivo).

## Pendiente

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

- [ ] **Arnés batch de pruebas de recursos**: recorrer todos los recursos vivos
  con `_preview_limit=3` y clasificar cada fallo (fuente caída / config rota /
  bug de fetcher). Tras la racha de 6+ recursos rotos detectados a mano, es la
  red de seguridad que falta.
- [ ] **Fuentes DIR3 rotas**: el CSV de datos.gob.es y el XLSX del PAe
  responden 404/HTML. Localizar las URLs vigentes y verificar la cabecera real
  del campo (oficial: `C_ID_UD_ORGANICA`). Bloquean el puente DIR3↔BDNS.
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
