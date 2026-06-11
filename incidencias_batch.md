# incidencias_batch.md — batería de fuentes "naturaleza religiosa"

Protocolo: las fuentes se VERIFICAN en vivo antes de manifestar (lección Manus).
Nada se commitea/despliega sin gatillo explícito (despliega / ejecuta / dale / sube).

## Estado

- [x] **RER (MAPER)** — OPERATIVO en master (4607391). manifests/rer_entidades.json.
      Especie HTML genérico, navigation=searchloop, pivote filtro.confesion.

- [x] **Fundaciones de competencia estatal** — DESPLEGADO. manifests/fundaciones_estatales.json
      Buscador: https://fundosbuscador.mjusticia.gob.es/fundosbuscador/
      Mecánica (probada en vivo 2026-06-11):
        · Sesión:     GET  cargaBuscador.action?lang=es_es  → JSESSIONID
        · Búsqueda:   POST buscarResultadoBusqueda.action   (pivote filtro.provincia, 52 prov.)
        · Paginación: GET  actualizarResultadoBusqueda.action?paginacion.index=N  (30/pág.)
        · Listado:    Nombre, Provincia, FINES (texto completo de fines — señal religiosa ya aquí)
        · Detalle:    DetalleFundacion.action?idFundacion=N  → fundadores, patronos, directivos
      Volumen: Madrid 3.089; total nacional ~ decenas de miles. Crawl mensual.
      Reutiliza el fetcher searchloop existente: SOLO manifiesto, sin código nuevo.
      Smoke test preview: 9.6s, NIF capturado (G…). Detalle trae NIF -> cruce directo con BDNS.

## Cola de fuentes por verificar (siguiente)

- [ ] Registros autonómicos de asociaciones (Madrid, CLM publican CSV — verificar URLs reales)
- [ ] BDNS — cruce para NIF (ancla letra R) por denominación normalizada RER/Fundaciones ↔ BDNS

## Notas de gobernanza ODM

- ODM es productor neutral: el manifiesto declara la fuente; el scoring de "naturaleza
  religiosa" (incl. filtrar por filtro.fines=religion) es del CONSUMIDOR, no de ODM.
  La cosecha neutral pivota por provincia y trae TODO; el filtrado por fines va aguas abajo.


## Nodriza de catálogo (DCAT) — DESPLEGADO

- [x] Especie "Catálogo DCAT" (CatalogFetcher): nave nodriza sobre datos.gob.es.
      modos=["extraer","descubrir"]. propose() emite 1 candidato autodescriptivo
      por distribución (target_fetcher_code + url + format). Verificado en vivo:
      51 candidatos asociaciones+fundaciones, 0 ruido.
- [x] Promoción heterogénea: ResourceCandidate gana target_fetcher_code/target_params
      (migración cand_target_1, IF NOT EXISTS). promote_candidate usa la especie-destino
      del candidato (padre DESCUBRE / hijo EXTRAE con File Download), no la del padre.
- [x] Hook propose() en el manager: descubridores de catálogo saltan infer()
      (que es agrupación por rutas, propia de Web Tree). Web Tree intacto.
- [x] Manifiesto madre: manifests/catalogo_asociaciones_fundaciones.json (genera_colecciones).

NOTA: esto SUPERSEDE manifestar a mano los 16 registros autonómicos: ahora se
      descubren. Tras desplegar: ejecutar la madre (discovering) y promover en UI
      los candidatos buenos (preferir CSV sobre JSON; Aragón trae 1 fichero/provincia).

## Diferido (siguiente fase)

- [ ] Recursión multinivel (meta-meta-recurso): relajar es_coleccion (hoy exige
      parent_resource_id IS NULL) a "raíz O nodo cualificado" + control de
      profundidad/ciclos en el discovering. El árbol (parent_resource_id) ya existe.


## Diseño — decisiones y notas (sin gatillo; recuperadas de conversación)

VOCABULARIO (fijado):
  · Pivote INTERNALIZADO  = un solo recurso itera todos los valores por dentro
    (bucle interno, p.ej. searchloop con search_field_values). Sale UN dataset.
  · Pivote EXTERNALIZADO = cada valor del pivote se saca a su propio recurso-hijo
    (N recursos, cada uno con su calendario/reintentos/versión/lease).

DECISIÓN — grano geográfico = COMUNIDAD AUTÓNOMA:
  · Externalizar a nivel CCAA (~17 nodos), NI nacional único (grueso) NI por
    provincia (explosión ingobernable, 52×N).
  · Cuando la fuente obliga a pivotar más fino (Fundaciones MAPER pide provincia),
    el nodo CCAA INTERNALIZA sus provincias: "Fundaciones de Andalucía" recorre
    sus 8 provincias por dentro. Árbol gobernable al grano elegido + pivote de
    acceso escondido en cada nodo. Los CSV autonómicos del catálogo ya vienen a
    grano CCAA de forma nativa → todo aterriza en CCAA sea cual sea el mecanismo.
  · Regla internal-vs-external POR FUENTE: externaliza si el pivote es partición
    natural Y aporta algo operativo (volumen, incremental, el consumidor quiere
    ese troceado). Internaliza si el pivote es solo mecanismo de acceso.

NOTA — pivote como TERCERA estrategia de descubrimiento:
  · Hoy hay 2 (Web Tree = árbol de ficheros; Catálogo DCAT = distribuciones).
  · Faltaría "descubridor de pivote": reutiliza el _discover_search_values del
    searchloop (que ya lee las opciones del <select>: confesiones, provincias) y
    emite un hijo por valor con target_params -> searchloop filtrado. Validar con
    UNA fuente (Fundaciones por CCAA) antes de generalizar. Conecta con la
    recursión multinivel diferida.

NOTA — series temporales (otro tema, aplazado):
  · Inverso de externalizar: COLAPSAR lo que parecen recursos distintos (un fichero
    por ejercicio) en UN recurso con `ejercicio` como parámetro runtime.
  · ODM ya roza esto: Web Tree detecta dimensiones year/month en infer(); el
    fetcher ATOM tiene ventana temporal + marca de agua `desde=auto`. Sería un
    tercer sabor: pedir un ejercicio concreto por param (default: último / todos).

WEB TREE — mejoras detectadas (PENDIENTE go/no-go — esto es 'el algo más'):
  · Unificar su promoción con el candidato ya autodescriptivo (target_fetcher_code/
    target_params): hoy el manager tiene una rama especial `is_child` que lee
    matched_urls/dimensions/path_template en runtime. Se podría colapsar -> menos
    código a medida. No aporta función nueva.
  · infer() (agrupación por patrón de ruta) es la pieza más frágil del
    descubrimiento; se rompe con portales de rutas irregulares. No tocar salvo
    que dé problemas en producción.
  · Veredicto provisional: simplificación menor, no urgente. Decidir si se hace.

## Cola UI (pendiente, sin gatillo)

- [ ] Lista de recursos: la columna "Apps" (aplicaciones) debe etiquetarse "Subsc."
      (suscripciones). Coherente con el rename Application->Subscriber ya en master.
      Buscar el header de columna en el componente de la tabla de recursos del frontend.

## UI merge/split de candidatos (Discovering.vue) — PENDIENTE, sin gatillo

Observación: merge/split poco intuitivos. Diagnóstico (código revisado):
- SPLIT: el modal pide pegar URLs crudas en <textarea> por grupo (group.urlsText,
  split por \n). Inusable con muchos URLs; sin drag&drop, patrón ni preview.
- MERGE: aceptable (checkbox + destino), pero ambos operan sobre matched_urls
  (abstracción Web Tree). Para candidatos de Catálogo DCAT (1 URL + target_params)
  merge/split no aplican y aun así se muestran -> desorienta. La UI no distingue
  el TIPO de candidato.

Mejoras propuestas (por valor):
1) SPLIT POR DIMENSIÓN, no por URLs: el candidato ya trae `dimensions`; ofrecer
   "partir por {provincia}/{CCAA}" y repartir solo. Edición manual = escape.
   Conecta con el modelo pivote/CCAA (partir por CCAA = operación natural).
2) ACCIONES SEGÚN TIPO de candidato: si es de catálogo (1 URL/target_params),
   mostrar solo promover/descartar; ocultar merge/split. Bajo esfuerzo, alto efecto.

## Arquitectura — modelo unificado de descubrimiento (consolidado)

JSONL = formato único interno. El manager vuelca cada registro a {exec}.jsonl
venga del fetcher que venga. CONSECUENCIA: el formato de origen es irrelevante
AGUAS ABAJO, pero NO en la aduana del parser — convertir bytes->dicts es donde el
formato manda (por eso hubo que añadir JSON a file_parsers). Para hijos de archivo,
inner_format (csv/json dentro del zip) sigue siendo necesario: elige el parser.

CUATRO estrategias de descubrimiento sobre el MISMO modelo de Colección
(modos=["extraer","descubrir"]); lo único que cambia es el "índice" del contenedor:
  · Catálogo DCAT   -> distribuciones (datos.gob.es)            [HECHO]
  · Web Tree        -> URLs hoja (árbol de ficheros)            [existe]
  · Pivote          -> valores de un <select> (provincia/CCAA)  [pendiente, reusa
                       searchloop._discover_search_values]
  · Archivo (ZIP)   -> miembros del archivo                     [pendiente, barato:
                       CompressedFileFetcher hoy es solo extractor de 1 entrada;
                       darle propose() que liste namelist() y emita 1 hijo/entrada
                       con target_params {url,format:zip,entry,inner_format}.
                       Umbral: 1 miembro=extrae, N=descubre. ZIP-de-ZIPs=recursión.]

TRES MECANISMOS ORTOGONALES (no confundir; no son redundantes):
  1) Colección/descubrimiento -> produce RECURSOS hijo (nuevas unidades de fetch).
  2) Pivote externalizado     -> parte UNA fuente en N recursos por filtro. Trocea
     el "cómo se trae". Grano de gobernanza decidido = CCAA.
  3) Derived dataset (pestaña Outputs / DerivedDatasetConfig) -> de UN stream ya
     volcado, proyecta una TABLA-DIMENSIÓN deduplicada por key_field, quedándose con
     extract_fields. SIN fetch nuevo. Corre como side-product (_derive_dataset, tras
     el dedup del staging). NO es congelar subconjuntos del pivote (error a evitar).
     Cautelas: acopla a nombres de campo (si no existen, recoge vacío en silencio);
     cada derived es un dataset más en leases/retención; NO usar para slicing de
     datos-hecho por filtro (eso es externalización).

APLICACIÓN AL ALGORITMO: derived dataset NIF<->denominación sobre RER/Fundaciones/
BDNS = primer ladrillo del ancla de la letra R, sin re-descargar. (El repo ya tiene
bdns_organos.json, que es este patrón.)

## UI — degatear descubrimiento de Web Tree (pendiente, sin gatillo)

El backend ya es genérico (hook propose() en el manager). Falta el frontend:
  · Discovering.vue (~L421-423): el desplegable filtra fetcher.code==='Web Tree'.
    Cambiar a fetcher.descubre / es_coleccion para poder lanzar y ver la Colección
    de Catálogo (que ya está en master pero no se puede disparar desde la UI; hoy
    solo corre por su schedule).
  · Collections.vue (~L23): copy "(hoy, Web Tree)" obsoleto.

## UI — filtro de recursos "solo descubribles" (pendiente, sin gatillo)
- En la lista de recursos, un checkbox para filtrar solo los que son Colección /
  descubribles (es_coleccion o fetcher.descubre). Vista rápida de las naves nodriza.

## Refactor — entidad Discoverer separada del Fetcher (DISCUTIR, post-BDNS)
Idea del usuario: extraer la capacidad de descubrir a una entidad propia
"Discoverer", elegida en función del Fetcher, en vez de un propose() pegado al
Fetcher. Motivación: Pivote y RestApi son "fetchers que no fetchean" (fetch()
NotImplementedError) — olor a dos responsabilidades en una clase. Separar:
Fetcher extrae, Discoverer descubre el índice y emite candidatos.
Preguntas a resolver:
  · ¿cómo se empareja Discoverer↔Fetcher? (registro fetcher→discoverer / el
    recurso declara su discoverer / mapping en seed)
  · los duales (Catálogo extrae Y descubre): ¿Fetcher con Discoverer asociado,
    o dos entidades?
  · el manager pasaría de hasattr(propose) a "¿tiene Discoverer? descubre : extrae".
  · ¿composición? el Discoverer reutiliza config del Fetcher (auth, base_url).
El BDNS RestApiDiscoverer será el 5º ejemplo concreto -> buen insumo para decidir
la forma del refactor con casos reales en la mano (catálogo/web-tree/pivote/
archivo/rest).
