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

### 8. Web Tree: qué dato producen los hijos (el parseo genérico no basta)
**Contexto**: el descubrimiento y la organización funcionan (series y bundles
con sus dimensiones), pero el CONTENIDO decepciona: los XLSX municipales tipo
'Informe PMP' no son tablas sino informes maquetados con UN dato útil por
fichero; el parseo tabular genérico produce filas-basura (pancartas, etiquetas,
celdas decorativas). Crítica del usuario, literal y certera: 'esto lo único que
produce es un directorio de URLs y con errores'.
**Opciones**:
  (a) *Registro documental* como modo por defecto de bundles y series no
  tabulares: una fila por fichero con {dimensiones, url, nombre, formato,
  fecha} y SIN intentar extraer contenido. Honesto, barato, útil como censo
  con linaje ('el directorio de URLs', pero a propósito y sin errores).
  (b) *Extracción dirigida (recetas)*: nuevo modo de extracción por recurso
  para ficheros-formulario — capturas declarativas tipo «la celda a la derecha
  de la etiqueta 'Periodo Medio de Pago Global'» → una fila limpia por fichero
  ({year, month, pmp_dias}). Coste moderado; convierte series como el PMP en
  datasets de verdad.
  (c) *Mejorar el parseo tabular genérico* (sniffing de cabeceras, descarte de
  pancartas). Ayuda en ficheros que SÍ son tablas; en los informes-formulario
  seguiría produciendo basura mejor alineada.
**Propuesta del usuario (2026-06)**: un fetcher tipo 'WebTreeIndexer' que no
parsee nada y entregue las URLs (útil para CKAN), dejando Web Tree para los
que se dejen extraer información.
**Refinamiento propuesto por Claude**: misma idea, pero como PARÁMETRO de la
especie en vez de especie nueva (especie = tecnología; aquí la tecnología es
idéntica y cambia el tratamiento de la salida). Nuevo param `extract_mode`
('datos'|'censo') materializado en DOS VARIANTES con candado:
  - 'Web Tree — Censo documental' 🔒 extract_mode=censo → una fila por fichero
    (dimensiones + url + nombre + formato), sin descargar ni parsear. Rápido,
    sin basura, insumo directo del CKAN (§9).
  - 'Web Tree — Extracción de datos' → comportamiento actual.
Ventajas sobre la especie aparte: cero duplicación (seed/factory/promote), un
hijo puede cambiar de variante sin recrearse (censo hoy, extracción cuando
exista receta), y el default al promover se decide con la auditoría
(bundle→censo, serie tabular→extracción). La distinción visible en UI la da el
nombre de la variante.
**Cifras de la auditoría (2026-06)**: 5 hijos tabla-real (127 ficheros), 31
informe-formulario (819), 28 pila documental (~2.180): el censo da valor
inmediato en 59/64; la extracción dirigida (b) rescataría los 31 del medio.
**Recomendación**: variante 'Censo documental' como (a) inmediato + (b)
recetas opt-in para series valiosas (PMP primero); (c) parseo genérico solo
para ficheros con tabla real.
**Estado**: DECIDIDA (2026-06, 'adelante' del usuario a la vía param+variantes).
Implementado: param extract_mode, variantes 'Censo documental' (🔒 censo) y
'Extracción de datos' (🔒 datos), y jerez_webtree.py v2 — UN directorio-censo
con todo el árbol + hijos de extracción solo para los TABLA_REAL de la
auditoría. Recetas (8b) IMPLEMENTADAS (2026-06, 'dale a 8b'): motor en
app/services/recetas.py (capturas declarativas {campo, etiqueta, tipo,
posicion?} con cascada celda→derecha→debajo y números en formato español;
gramática única para XLSX/PDF vía rejilla), tercer extract_mode 'receta' con
variante 'Extracción con receta' 🔒, param `receta` por recurso. Piloto PMP
verificado en vivo: 27 ficheros → una fila limpia por mes (2026-01: 84,89
días...). Quedan ~30 informes-formulario esperando su receta en la whitelist
RECETAS de jerez_webtree.py.
**Doctrina de las recetas (2026-06, reparo del usuario sobre la generalidad)**:
una receta es DATO declarativo del recurso (la categoría de url_template o
field_map), nunca código; el motor de la especie es general y no sabe de
portales. Guardarraíl contra la deriva: la gramática de capturas es
vocabulario de la ESPECIE y solo crece por decisión de diseño deliberada
(aquí, en DECISIONES), jamás por hack para un fichero rebelde — el fichero
que no quepa en la gramática se queda en censo, no fuerza la gramática. El
día que una receta necesite condicionales habrá dejado de ser dato: ese es el
límite. (La alternativa plugeable-código existe como gancho custom_parser
heredado y se desaconseja por recurso: convertiría 'crear un recurso' en
'desplegar código'.)
**Ratificada (2026-06)**: se evaluó la vía 'param solo en el recurso, sin
variantes' (propuesta del usuario) — funcionalmente equivalente y ya posible
hoy. Se mantienen las dos variantes por una única razón: etiqueta veraz en el
listado (la columna dice censo/extracción de un vistazo y el candado garantiza
que el rótulo no miente). 'Lo dejamos como está'.

### 9. Alimentación automática de un CKAN para Jerez desde los hijos Web Tree
**Contexto** (idea del usuario, 2026-06): aprovechar el output actual —
directorios organizados de URLs con dimensiones — para poblar automáticamente
un portal CKAN de Jerez. Cierra el círculo del brief germinal del Web Tree
(chat.md: 'poblar CKAN correctamente... usar ODM como motor de ingestión') y
convierte la debilidad en virtud: un dataset CKAN no necesita filas parseadas,
necesita metadatos + enlaces — exactamente lo que el censo ya produce.
**Mapeo natural**: hijo Web Tree (serie/bundle) → package CKAN (título,
descripción, organización=Ayto. Jerez, tags por tema); cada matched_url →
resource del package (url, formato, nombre con periodo); dimensiones → extras;
re-discover del crawler → packages actualizados con los ficheros nuevos.
**Opciones**:
  (a) *Exportador batch* (scripts/publicar_ckan_jerez.py): sincroniza datasets
  CKAN desde los hijos vía Action API (package_create/update, api key).
  Barato, desacoplado, mismo patrón que cruce_curacion.
  (b) *Catálogo DCAT cosechable*: ODM expone un data.json/DCAT generado de los
  hijos y el CKAN lo cosecha con su harvester nativo. Acoplamiento cero (CKAN
  tira), estándar, sirve también para uData/data.europa.
  (c) *Integración de plataforma*: entidad 'destino de publicación' + sync
  automático post-discover. Más infra; solo si esto se vuelve recurrente y
  multi-portal.
**Recomendación**: (a) para validar rápido con el CKAN de Jerez; evolucionar a
(b) en cuanto funcione (DCAT es la versión 'ODM produce piezas' de esta idea:
publicamos el catálogo, quien quiera lo cosecha). (c) solo con demanda real.
**Dependencia**: decide junto con §8 — el censo (8a) es justo el insumo de
este proyecto; las recetas (8b) enriquecerían los packages con datos tabulares.
**Clarificación (2026-06, duda del usuario '¿CKAN tendrá problemas para
clasificar?')**: la clasificación NO sale del recurso-directorio único, sino
de las CANDIDATAS del crawler, que persisten aunque no se promuevan: una
candidata = un package CKAN (plantilla → serie, suggested_name → título,
dimensiones → extras, matched_urls → resources). El directorio es la cara del
censo dentro de ODM; además sus filas llevan columna 'seccion' derivada del
path como clasificación embebida.
**Afinado (2026-06, 'los títulos hacen falta, pero sin artificios de más')**:
las candidatas no-promovidas YA NO se persisten. El inferer es función pura:
el exportador CKAN llamará a infer() en memoria sobre el censo para obtener
los grupos con título ('Informe PMP (mensual)') en el momento de exportar.
Títulos finos sin estado residual: solo persisten las 5 candidatas de los
recursos promovidos.
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

### 11. Recursos propuestos por aplicaciones: aprobación del admin
Contexto (decisión del usuario, 2026-06): las aplicaciones dejan de crear
recursos de forma autoritaria. Un recurso creado por una aplicación nace
PROPUESTO y no se ejecuta ni se programa hasta que el admin de ODM lo aprueba;
en el alta, la aplicación además SOLICITA un schedule, que el admin aprueba
(o ajusta) junto con el recurso.

Forma recomendada (a caracterizar/montar):
- Resource gana un estado de aprobación explícito:
  `estado_aprobacion` ∈ {propuesto, aprobado, rechazado} (default 'aprobado'
  para altas de admin/UI/sistema; 'propuesto' cuando la procedencia es
  'aplicacion'). Enum explícito —no un booleano— porque el rechazo es un
  desenlace real y queremos auditoría (quién pidió, quién aprobó/rechazó,
  cuándo, motivo).
- Gating: run() y schedule SOLO operan si estado_aprobacion=='aprobado'. Un
  recurso propuesto es inerte.
- Schedule solicitado: el alta de la app incluye la frecuencia deseada, que se
  guarda como SOLICITUD (p. ej. `schedule_solicitado` JSONB en el recurso o una
  fila de schedule en estado 'pendiente'). Al aprobar, el admin confirma o
  edita y se materializa el Schedule real.
- UI: bandeja de PROPUESTAS para el admin (recurso + app peticionaria + schedule
  pedido), con aprobar/rechazar. Mutaciones `aprobarRecurso(id, schedule?)` y
  `rechazarRecurso(id, motivo)`. Permiso RBAC nuevo: 'recursos.aprobar'.
- Disparador: procedencia 'aplicacion' → nace propuesto; usuario/sistema/ui →
  aprobado. La mutación de creación expuesta a las apps fija estado='propuesto'.
- Interacción con `active`: 'active' sigue siendo el on/off una vez aprobado;
  estado_aprobacion gobierna si SIQUIERA puede activarse.
Estado: especificado, pendiente de montar.
