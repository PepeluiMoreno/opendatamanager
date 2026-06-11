# Diseño: Colecciones, descubrimiento y batería de fuentes "naturaleza religiosa"

> Registro de decisiones y razonamiento de la sesión, para retomar el trabajo en
> otra sesión con todo el contexto. Complementa `incidencias_batch.md` (que lleva
> los pendientes accionables); este documento es la narrativa y el porqué.
> Última actualización: 2026-06-11.

## 1. Objetivo del proyecto

Obtener el censo más exhaustivo posible de **fundaciones, asociaciones y demás
entes religiosos** en España, para alimentar un **algoritmo de naturaleza
religiosa** (motor léxico determinista, sin IA) que identifica beneficiarios
religiosos en gasto público (BDNS) y patrimonio (inmatriculaciones). Ancla
determinista: la **letra R del NIF** + cruce por denominación normalizada.

ODM es **productor neutral**: descubre, cosecha y entrega datos. El scoring de
naturaleza religiosa y la normalización de esquemas heterogéneos son del
**consumidor** (ckan-jerez o el servicio del algoritmo), nunca de ODM.

## 2. Lección transversal (origen: Manus)

El punto de partida fue un documento de Manus que proponía recursos **alucinados**
(un "Power BI del Ministerio" para el RER que no existe; un RNA estatal con CSV
que no se publica; URLs de catálogo confundidas con recursos). Regla adoptada:
**toda fuente se verifica EN VIVO antes de manifestarse.** Y su corolario, surgido
al desarrollar la Colección: **no basta verificar el descubrimiento; hay que
verificar que los HIJOS extraen** (formato, separador, encoding, JSON anidado).

## 3. Estado de fuentes (verificadas y desplegadas)

| Fuente | Mecánica | Estado |
|---|---|---|
| **RER** (Registro Entidades Religiosas) | MAPER Struts: sesión→POST buscarRER (pivote `filtro.confesion`)→paginación `avanzarRetrocederRER`→detalle `DetalleEntidadReligiosa`. Especie HTML genérico, `navigation=searchloop`. NO publica NIF/fines/culto. | Operativo |
| **Fundaciones de Competencia Estatal** | `fundosbuscador` Struts: sesión `cargaBuscador`→POST `buscarResultadoBusqueda` (pivote `filtro.provincia`)→paginación `actualizarResultadoBusqueda?paginacion.index=N`→detalle `DetalleFundacion`. El detalle TRAE NIF (oro para el cruce). | Desplegado |
| **Catálogo registros autonómicos asoc./fund.** | Colección (Catálogo DCAT) sobre datos.gob.es. Descubre 1 hijo por distribución CSV/JSON. ~26 distribuciones de asociaciones. | Desplegado; pendiente lanzar discovery y promover hijos |

Detalles de mecánica de RER y Fundaciones en `docs/fuente_rer_maper.md` y en los
manifiestos (`manifests/rer_entidades.json`, `manifests/fundaciones_estatales.json`).

## 4. Arquitectura de descubrimiento (el corazón de la sesión)

### 4.1 JSONL es el formato único interno
El manager vuelca cada registro a `{exec}.jsonl`. El formato de origen es
irrelevante **aguas abajo**, pero NO en la aduana del parser (bytes→dicts). Por eso
se añadió soporte JSON a `file_parsers`. Para hijos de archivo, `inner_format`
sigue siendo necesario: elige el parser.

### 4.2 Colección = recurso con capacidad "descubrir"
El nombre canónico es **Colección** (ya en el modelo: `es_coleccion`,
`genera_colecciones`, `Collections.vue`, 🛰️). "Nave nodriza" es coloquial.
`Fetcher.modos` declara la capacidad (`["extraer","descubrir"]`). `es_coleccion`
requiere: fetcher que descubre + recurso-madre (`parent_resource_id IS NULL`) +
intención (`genera_colecciones`).

### 4.3 Cuatro estrategias de descubrimiento, un solo modelo
Lo único que cambia es el "índice" del contenedor:
- **Catálogo DCAT** → distribuciones (datos.gob.es). HECHO.
- **Web Tree** → URLs hoja de un árbol de ficheros. Existía.
- **Pivote** → valores de un `<select>` (provincia/confesión). PENDIENTE; reutiliza
  `searchloop._discover_search_values`.
- **Archivo (ZIP/TAR)** → miembros del archivo. PENDIENTE; `CompressedFileFetcher`
  hoy es solo extractor de una entrada. Un ZIP multi-fichero ES una Colección.

### 4.4 Tres mecanismos ortogonales (no confundir)
1. **Colección/descubrimiento** → produce RECURSOS hijo (nuevas unidades de fetch).
2. **Pivote externalizado** → parte UNA fuente en N recursos por un filtro. Trocea
   el "cómo se trae".
3. **Derived dataset** (pestaña Outputs / `DerivedDatasetConfig`) → de un stream ya
   volcado, proyecta una TABLA-DIMENSIÓN deduplicada por `key_field` con
   `extract_fields`. SIN fetch nuevo. Side-product (`_derive_dataset`).

### 4.5 Internalizar vs externalizar un pivote (vocabulario fijado)
- **Internalizado**: un recurso itera todos los valores por dentro → UN dataset.
- **Externalizado**: cada valor → su propio recurso hijo → N datasets gobernables
  por separado (calendario/reintentos/versión/lease).
- **Decisión de grano geográfico = COMUNIDAD AUTÓNOMA** (~17 nodos). Ni nacional
  único (grueso) ni por provincia (explosión, 52×N). Si la fuente obliga a pivotar
  más fino (Fundaciones pide provincia), el nodo CCAA INTERNALIZA sus provincias.
- Regla POR FUENTE: externaliza si el pivote es partición natural Y aporta algo
  operativo; internaliza si es solo mecanismo de acceso.

## 5. Qué se tocó en el código (esta sesión)

- `app/fetchers/searchloop_html.py`: searchloop como variante `navigation` de HTML;
  enlace de detalle por fila; enriquecimiento listado→detalle (`detail_level`);
  extracción por etiqueta robusta; preview acotado (1 pivote, sin delays, detalle
  de pocas filas) para no agotar el gateway (504).
- `app/fetchers/html_generic.py`: delega `navigation=searchloop`.
- `app/models.py`: `ResourceCandidate` += `target_fetcher_code`, `target_params`
  (promoción heterogénea: padre DESCUBRE, hijo EXTRAE con otra especie).
- `app/manager/fetcher_manager.py`: hook `propose()` — descubridores de catálogo
  emiten candidatos ya formados y saltan `infer()` (que es agrupación por rutas,
  propia de Web Tree). Web Tree intacto.
- `app/graphql_api/mutations.py`: `promote_candidate` usa `target_fetcher_code`/
  `target_params` del candidato si existen; si no, comportamiento legacy.
- `app/fetchers/catalog.py`: NUEVA especie "Catálogo DCAT". `propose()` consulta
  apidata, regla de selección (include/exclude regex + formatos + drop diccionarios),
  emite candidato autodescriptivo por distribución.
- `app/fetchers/file_parsers.py`: soporte JSON (array, `records_path`, autodetección
  de envoltorio, aplanado de anidados, encoding utf-8→latin-1 fallback). +`.json`.
- `seed_fetchers.py`, `app/fetchers/fetchers_enum.py`: registrada la especie con
  `modos=["extraer","descubrir"]`.
- Migración `cand_target_1` (ADD COLUMN IF NOT EXISTS, por el re-run de Alembic).
- Manifiestos: `rer_entidades.json`, `fundaciones_estatales.json`,
  `catalogo_asociaciones_fundaciones.json`. Eliminados los alucinados de Manus.

## 6. Verificaciones en vivo hechas (para no repetir)

- RER: flujo completo, 42/42 entidades CONF_JU con 12 campos, 0 nulos críticos.
- Fundaciones: Madrid 3.089; detalle con NIF (ej. G28798551); preview 9.6s.
- Catálogo: 51 candidatos asoc.+fund., 0 ruido; nombres desambiguados.
- Hijos asociaciones (extracción real): CSV OK en Canarias (NIF), CLM, Madrid,
  JCyL (NIF). JSON OK en Aragón y CLM-json. Pendientes de param por hijo: Asturias
  (`delimiter`), CARM (`records_path`), Xunta (`headers`). Ruido: Euskadi coló una
  distribución económica.

## 7. Pendiente (ver `incidencias_batch.md` para el detalle accionable)

- **UI**: degatear descubrimiento de Web Tree → `fetcher.descubre` (Discovering.vue
  ~L421, Collections.vue copy ~L23). Sin esto, la Colección de Catálogo solo corre
  por schedule, no se lanza/ve a mano.
- **Especie Pivote** (4ª estrategia), validar con Fundaciones por CCAA.
- **Archivo como Colección**: `CompressedFileFetcher` → `propose()` por entradas.
- **`prefer_format`** en el catálogo (CSV vs JSON cuando hay ambos) para reducir hijos.
- **Derived dataset NIF↔denominación** sobre RER/Fundaciones/BDNS = primer ladrillo
  del ancla de la letra R.
- **UI merge/split** de candidatos: split por dimensión, no por URLs; acciones según
  tipo de candidato.
- **Recursión multinivel** (diferida): relajar `es_coleccion` ("raíz O nodo
  cualificado") + control de profundidad/ciclos. El árbol (`parent_resource_id`) ya
  existe; la promoción ya es heterogénea.
- **Cola UI menor**: columna "Apps"→"Subsc." en lista de recursos.

## 8. Cola de fuentes siguientes

Registros autonómicos de **fundaciones** (mismo catálogo, otra rama); BDNS para el
NIF; inmatriculaciones (fichero publicado 2021, cruce patrimonial). Verificar en
vivo antes de manifestar.
