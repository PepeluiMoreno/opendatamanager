# Arnés de recursos — pasada del 2026-06-07

**42 recursos activos probados** con `_preview_limit=3` (paralelo 7, timeout 60s).
Resumen tras retests dirigidos: **34 OK · 4 sin filas · 3 fuente caída · 1 pendiente conocido**.

## Sanos (34)
Los 16 feeds PLACSP CODICE, INE (población, provincias, catálogos), FACE,
Fiscalías, SEPE, Hacienda Deuda Viva, datos.gob.es Catálogo, BDNS y resto de
manifiestos. **DIR3 - Unidades Orgánicas: FUNCIONA** (126.368 filas) — el ítem
"fuentes DIR3 rotas" del backlog estaba desfasado; solo era lento (timeout 240
fijado en seed).

## Fuente caída (3) — el problema está fuera
| Recurso | Diagnóstico |
|---|---|
| Hacienda - PMP Entidades Locales | 404 en serviciostelematicosext.hacienda.gob.es — URL movida, buscar la vigente |
| Registros de la Propiedad (CORPME) | 404 en registradores.org/documents/... — documento renombrado |
| Geonames - ES.zip | HTTP 503 persistente (throttling del servidor); transitorio, reintentar otro día |

## Sin filas (4) — la fuente responde, la extracción no
| Recurso | Diagnóstico |
|---|---|
| Jerez (Deuda, Morosidad, PMP) ×3 | Las URLs `{year}` devuelven 404-HTML: el portal cambió las rutas. RESUELTO 2026-06-07: base movida a `/fileadmin/Documentos/Transparencia/a-infopublica/a07-economica/c-deuda/{year}/`; nombres inestables entre años → templatizar es inviable, usar el Web Tree crawler (ver BACKLOG y seed_resources.py) |
| OSM - Inmuebles Eclesiásticos | Consulta España-entera no cabe en una preview de 60s (Overpass vivo: verificado con bbox pequeño). Limitación del arnés, no del recurso |

## Arreglado en esta pasada
- **Catastro - Parcelas (Sevilla)**: el bbox estaba en lon,lat y el WFS INSPIRE
  exige lat,lon (verificado en vivo: con el eje correcto devuelve parcelas).
  Corregido en seed. Pendiente aparte: la petición provincia-entera con
  count=500 tumba el servidor (500 tras 233s) → trocear (backlog).
- **Clasificador del arnés**: HTTP 4xx/5xx envueltos en RuntimeError ya
  clasifican como FUENTE CAÍDA (Geonames salía como BUG).
- **Arnés paralelizado** (--paralelo, tope por futuro): la pasada completa
  cabe en ~12 min.

## Único pendiente conocido
- **RER - Entidades Religiosas**: el portal migró a Power BI; necesita capturar
  el `query_json` real (ya estaba en backlog, `config_rer.md`).
