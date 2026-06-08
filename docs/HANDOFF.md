# HANDOFF — ODM · cierre de sesión 2026-06-06

## Arranque de la próxima sesión (protocolo)
1. Sincronizar SIEMPRE primero: `git fetch <PAT-remote> master && git reset --hard FETCH_HEAD`.
   HEAD esperado: `cfe1eaf` (o posterior). El PAT de la racha quedó expuesto en
   chat → **rotarlo**; el remoto usa `https://x-access-token:<PAT>@github.com/PepeluiMoreno/opendatamanager.git`.
2. El sandbox se reinicia con instantáneas viejas sin avisar: la verdad es
   GitHub; verificar pushes con `git ls-remote`.
3. Local: postgres odm/odm, schema opendata, `alembic upgrade heads`,
   `python seed_fetchers.py`. Suite: `pytest tests/ -q --ignore=tests/integration` (170 verdes).
4. Frontend: `cd frontend && npm run build` debe quedar verde antes de cada push
   (un build roto redeploya prod a un fallo).

## Reglas de oro de prod
- Cada push REDEPLOYA y MATA procesos en curso (ventana 502 de nginx 30-60s).
  El `deploy-healthcheck.patch` del backlog es para cerrar esa ventana: PENDIENTE
  y recomendado como lo primero.
- El entrypoint borra alembic_version en cada boot → TODA migración IF NOT EXISTS
  pura (verificado idempotente para las de esta sesión).
- Scripts en prod: lanzar con `python -u` para ver el log en directo.

## SHIPPEADO esta sesión (todo en master)
- **§8b Recetas** (e..): motor app/services/recetas.py (capturas declarativas,
  cascada celda→derecha→debajo, números es), 3er extract_mode 'receta' + variante
  con candado, piloto PMP verificado en vivo. Doctrina anti-deriva en DECISIONES.
- **Parser**: poda de columnas vacías + filtro de filas-leyenda ('( a )','c=a+b').
- **Bautizador** (naming.py): código solo en sección de 1er nivel (A07), acentos,
  camelCase, dedupe, sin {placeholders} ni paréntesis.
- **Web Tree**: cata de descubrimiento en el Test del crawler padre; directorio-
  censo singleton (libera nombre/tabla de cualquier ocupante).
- **Collections (COMPLETA, back+front)**: keystone `fetcher.modos` [extraer/
  descubrir] (Fetcher.descubre, Resource.es_coleccion); procesos tipados
  `resource_execution.kind` [extraccion/discovering]; query GraphQL `collections`
  + sección de sidebar 🛰️ con candidatos/miembros/último rastreo; drill-down a
  candidatos conservado; terminología 'miembro'; hint en el alta.
- **UI**: Paginator.vue + usePagination; panel de Schedule abajo; TODA tabla de
  datos paginada (Resources ya; +Publishers, DataExplorer, Collections, Usuarios,
  Trash, Applications, Subscriptions, MisDatos). Dashboard son tarjetas, no tabla.

## PENDIENTE — cadenas de aplicaciones (especificadas, sin montar)
- **§12 Alta y auth M2M** (CIMIENTO, va primero): SolicitudIngreso → admin aprueba
  → principal 'aplicacion' + TOKEN (hash en reposo, display-once, sin caducidad
  por decisión del usuario, rotación/revocación, prefijo odm_app_, compare_digest,
  Bearer/HTTPS, scopes POR ACCIÓN). Modelo: SolicitudIngreso, Application,
  ApplicationToken; middleware Bearer. RBAC 'aplicaciones.aprobar'.
- **§11 Recursos propuestos**: `estado_aprobacion` {propuesto|aprobado|rechazado}
  (propuesto si procedencia 'aplicacion'); run()/schedule gatean a 'aprobado';
  schedule solicitado por la app, aprobado por el admin; bandeja de propuestas;
  RBAC 'recursos.aprobar'.

## PENDIENTE — otros
- Tejado: deploy-healthcheck.patch (URGENTE), `seed_resources.py` en prod, rotar PAT.
- Recetas siguiente tanda: morosidad trimestral, liquidaciones-carátula (whitelist
  RECETAS en scripts/jerez_webtree.py).
- Promoción manual: selector de variante (ya hecho, 861034f) ✓.
- Parser PDF-prosa: detectar no-tabla → 0 filas (caso Plan Estratégico).
- Fuentes rotas: Hacienda PMP EELL (404), CORPME (404), Geonames (503), Catastro
  Sevilla (trocear).
- Processes UI: el usuario quiere rediseñarla con badge de tipo (kind ya expuesto)
  y filtro por rango de fechas.
- §9 CKAN Jerez: la estratégica, esperando 'adelante' (insumo censo ya servido).

## Manual de usuario
docs/ (o /mnt/user-data/outputs/MANUAL_USUARIO_ODM.md): redactado sobre el UI
actual, incluye especies/variantes/exploración (search loops), Collections y
todas las secciones. Pendiente de commitear a docs/ si se desea.
