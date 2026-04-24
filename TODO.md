# TODO

## Despliegue y CI/CD

- Migrar el despliegue de produccion a imagenes inmutables publicadas en `ghcr.io`, evitando `git pull` en el servidor.
- Separar claramente `build` y `deploy`:
  - CI construye y publica imagenes.
  - Produccion solo hace `docker compose pull` y `docker compose up -d`.
- Definir imagenes versionadas por tag y/o SHA de commit para facilitar rollback y trazabilidad.
- Cambiar `docker-compose.prod.yml` para usar `image:` en backend/frontend en lugar de `build:`.
- Mantener `.env.production` fuera del repo e inyectarlo solo como secreto en entorno de despliegue.
- Reducir el codigo presente en produccion al minimo necesario:
  - idealmente solo `compose`, `env` y volumenes persistentes.
- Evaluar si conviene un repositorio/stack de despliegue separado del repositorio de aplicacion.

## Endurecimiento adicional

- Revisar si el usuario de despliegue puede reducir permisos en host sin perder capacidad operativa.
- Mantener contenedores sin root donde sea posible.
- Documentar estrategia de rotacion de secretos y claves SSH.
- Documentar procedimiento de rollback de despliegue.

## Portal Documental — extensión futura: auto-generación de recursos (Opción B)

### Contexto

El fetcher `Portal Documental` actualmente funciona como **recurso único con taxonomía**
(Opción A): un solo recurso crawlea toda una sección del portal, descarga los ficheros
y almacena `seccion`/`subseccion` como metadatos en la tabla destino. La taxonomía se
consulta via el schema GraphQL de datos (`/graphql/data`).

### Qué aportaría la Opción B

Un modo de **descubrimiento** en el que el crawler recorre el portal, identifica los
nodos hoja (páginas finales con ficheros descargables) y los agrupa por nivel de
profundidad o patrón de URL. Cada grupo se convertiría en un `Resource` hijo
independiente, heredando el fetcher y los params del padre pero con `start_url`
acotado a esa sección. Cada hijo podría tener su propio `schedule`, pausarse o
reejecutarse de forma autónoma.

### Decisión de diseño: el fetcher no crea recursos

El fetcher no debe ser responsable de crear entidades `Resource` — eso rompería
la abstracción. La generación de recursos hijos la ejecutaría un paso de
orquestación separado (el `ResourceManager` o un endpoint de la API de administración)
a partir del resultado del discover, no el propio fetcher.

### Qué habría que crear

- **Modo `discover` en `PortalDocumentalFetcher`**: en lugar de descargar ficheros,
  devuelve la lista de nodos hoja descubiertos con su URL, profundidad, patrón y
  muestra de extensiones encontradas. Se almacena como artefacto de la ejecución
  (p.ej. en `staging_path`).
- **Mutación GraphQL `discoverPortalResources(resourceId)`**: lee el artefacto de
  discover más reciente de ese recurso, agrupa los nodos por patrón/profundidad y
  llama a `createResource` por cada grupo, marcándolos con `parent_resource_id`.
- **Campo `parent_resource_id` en `Resource`** + migración Alembic correspondiente.
- **Vista en el frontend**: lista los recursos hijos de un recurso padre (pestana
  "Secciones descubiertas") y permite aprobar/rechazar cada grupo antes de crear.

### Qué habría que modificar

- `ResourceExecution`: añadir campo `discover_artifact` o reutilizar `staging_path`
  para almacenar el JSON de nodos descubiertos.
- `seed_resources.py` / import bundle: los recursos generados automáticamente
  necesitan un flag `auto_generated: true` para distinguirlos de los manuales.
- Frontend `Resources.vue`: mostrar badge "auto" en recursos generados y enlace
  al recurso padre.

### Qué habría que eliminar

- Una vez migrado a Opción B, el recurso único `jerez_transparencia_economica_xlsx`
  (Opción A) se puede retirar o degradar a recurso padre de solo descubrimiento,
  sin `target_table` propio.

---

## Propuesta de siguiente fase

- Fase actual:
  - desplegar con el flujo endurecido ya preparado.
- Fase siguiente:
  - migrar completamente a GHCR como mecanismo principal de entrega para las ultimas fases del proyecto.
