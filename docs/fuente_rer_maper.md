# Fuente RER — MAPER (Ministerio de Justicia) — VERIFICADA

Fecha de verificación: 2026-06-11. Sustituye a la propuesta de Manus basada en
un supuesto Power BI del Ministerio, que **no existe**. La fuente real es el
buscador MAPER (Struts2):

## Mecánica (probada en vivo)

1. **Sesión**: `GET /Maper/buscarRER.action` → cookie `JSESSIONID`.
2. **Búsqueda**: `POST /Maper/buscarRER.action` multipart con campos `filtro.*`
   y compañeros `__multiselect_*`. Fija los criterios en la sesión del servidor.
3. **Paginación**: `GET /Maper/avanzarRetrocederRER.action?page=N` sobre la
   misma sesión. **Action distinto al del formulario**. Acepta GET y POST.
   Enlace "Siguiente": `li.movimiento a:-soup-contains('Siguiente')`.
4. **Listado**: `table.tabla_datos` con solo 4 columnas (Nombre, Comunidad,
   Provincia, Municipio) + enlace de detalle con `numeroInscripcion`.
5. **Detalle**: `GET /Maper/DetalleEntidadReligiosa.action?numeroInscripcion=N`.
   Campos en `.detallePublicacionTexto` con patrón
   `<p><strong>Etiqueta</strong>: valor</p>` (valor en nodo de texto),
   representantes legales en `<ul>`, federaciones en `<table>`.

## Implementación en ODM

Especie **HTML (genérico)** con `navigation=searchloop` (variante; delega en
`searchloop_html`). El Modo A se extendió con: captura de href por fila
(`row_link_selector`), enriquecimiento listado→detalle (`detail_level`, mismo
esquema que `levels`) y extracción por etiqueta robusta (coincidencia exacta,
nodos de texto, listas y tablas). Manifiesto: `manifests/rer_entidades.json`.

Pivote: `filtro.confesion` (16 valores autodescubiertos del `<select>`).
Volumen: ~21.840 entidades / ~2.184 páginas. Con los delays del manifiesto la
cosecha completa ronda 7-8 h → schedule mensual nocturno.

Prueba end-to-end: confesión JUDÍOS, 42/42 entidades con detalle completo,
cero nulos en campos críticos.

## Esquema real del detalle (12 campos)

numero_inscripcion, numero_inscripcion_antiguo, confesion, seccion, nombre,
fecha_inscripcion, tipo_entidad, domicilio_social, comunidad_autonoma,
fecha_estatutos, representantes_legales (lista "|"), federaciones (tabla "|").

## Implicaciones para el algoritmo de naturaleza religiosa

- El RER público **NO publica NIF, fines, ni lugares de culto** (Manus los
  inventó). El ancla determinista (letra R del NIF) debe venir del cruce con
  BDNS/AEAT por denominación normalizada, no del RER.
- Señales que SÍ aporta el RER: confesión y sección oficiales, tipo de entidad,
  pertenencia a federaciones (señal fuerte), domicilio y representantes
  (útiles para desambiguación en cruces).
- Fuentes descartadas por no verificables: RNA estatal (no publica CSV/JSON del
  registro completo) y Directorio de Lugares de Culto (la URL propuesta era la
  página de catálogo, no el recurso). Si se retoman, exigir verificación en
  vivo antes de crear manifiesto.
