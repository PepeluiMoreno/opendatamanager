# TODO

## Despliegue y CI/CD

> Mayoritariamente HECHO. `docker-compose.prod.yml` usa imágenes ghcr.io,
> `.github/workflows/deploy.yml` construye y publica, `.env.production` está
> fuera del repo (sólo `.env.production.example`).

Pendiente:

- Versionar imágenes por SHA de commit además de `:latest` para facilitar rollback.
- Decidir si conviene un repositorio/stack de despliegue separado del repositorio de aplicación.

## Endurecimiento — documentación

- Documentar estrategia de rotación de secretos y claves SSH.
- Documentar procedimiento de rollback de despliegue.
- Revisar si el usuario de despliegue puede reducir permisos en host sin perder capacidad operativa.

## Apificación de portales web clásicos — `WebTreeFetcher` + `ResourceCandidate`

Diseño autoritativo: [`docs/web_tree_fetcher_design.md`](docs/web_tree_fetcher_design.md).

Sustituye **3 implementaciones solapadas en master** (LegacyDataPortalFetcher,
PortalFilesCataloguer, flujo discover-secciones-children directos) por una única
ruta basada en:

- Un fetcher único `WebTreeFetcher` con modos `discover` y `stream`.
- Un servicio `GroupingInferer` que infiere agrupaciones por patrones de URL
  (year, mes, trimestre, fecha completa, DIR3, genérico).
- Una entidad `ResourceCandidate` con ciclo `discovered → reviewed → promoted | discarded | merged | split`.
- `Discovering.vue` refactorizado: muestra candidatos en lugar de "secciones del JSON-artifact".
- Resources hijos (auto_generated) que se programan con la UI de scheduling existente.

### Tareas

**Backend**

- [ ] Migración Alembic: tabla `resource_candidate` (campos en el spec).
- [ ] Modelo `ResourceCandidate` en `app/models.py`.
- [ ] `app/fetchers/web_tree_fetcher.py` con modos `discover` (output puro, sin BD) y `stream`.
- [ ] `app/services/grouping_inferer.py` con reconocedores year/mes/trimestre/fecha/DIR3/genérico.
- [ ] `app/manager/fetcher_manager.py`: post-`discover`, invocar `GroupingInferer` y persistir candidatos.
- [ ] `app/fetchers/fetchers_enum.py`: registrar `WEB_TREE`.
- [ ] GraphQL: queries `resourceCandidates`, `resourceCandidate(id)`; mutations `promoteCandidate`, `discardCandidate`, `mergeCandidates`, `splitCandidate`.
- [ ] Borrar: `legacy_data_portal.py`, `portal_files_cataloguer.py`, `_discover_mode` runtime, `discover_artifact*` queries, `create_child_resources` mutation.

**Frontend**

- [ ] `frontend/src/api/graphql.js`: operaciones de candidatos.
- [ ] `frontend/src/views/Discovering.vue`: refactor para listar y operar sobre candidatos.
- [ ] `frontend/src/views/Resources.vue`: retirar `isDiscoverable()` y `DiscoverModal`.
- [ ] Borrar: `frontend/src/views/DiscoverModal.vue`.

**Documentación**

- [x] Diseño autoritativo en `docs/web_tree_fetcher_design.md`.
- [x] README.md: Portal Documental → Web Tree.
- [x] `docs/resource_bundle_import.md`: ejemplos con `Web Tree`.

## UI — estandarización de modales

Estándar definido en `frontend/src/assets/styles.css`: `.modal-overlay` (centrado),
`.modal-card` (768px), `.modal-card-sm` (480px), `.modal-card-lg` (1024px). Todos
con `max-w-92vw / max-h-85vh` para móvil. Aplicado a los modales nuevos
(`Discovering` promote, `DataExplorer` params).

Pendiente: sweep de los modales restantes en
`PreviewResourceModal`, `PreviewDataModal`, `CreateEditFetcherModal`,
`FetcherDetailModal`, `Fetchers.vue`, `Resources.vue`, `Applications.vue`,
`Publishers.vue`, `Subscriptions.vue`, `Executions.vue`, `Trash.vue`,
`ResourceTest.vue` para usar las clases comunes.

## Propuesta de siguiente fase

Tras cerrar la apificación con WebTree, evaluar la separación explícita de fases
del pipeline (fetch / scrape / process / normalize / publish) y la introducción
de un `CKANPublisher` como destino. Aplazado deliberadamente — no contamina la
fase actual.
