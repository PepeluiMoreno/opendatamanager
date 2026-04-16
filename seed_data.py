"""
Seeding inicial de OpenDataManager.
Idempotente: safe to run on every startup. Uses upsert-by-name semantics.

Orden:
  1. Fetchers   — sincroniza tipos de fetcher desde el código
  2. Publishers — organismos base del estado español
  3. Resources  — recursos fundacionales (referencia: DIR3, geografía)
"""
import json
import uuid
from app.database import SessionLocal
from app.models import Application, DatasetSubscription, Fetcher, FetcherParams, Publisher, Resource, ResourceParam


# ---------------------------------------------------------------------------
# 1. FETCHERS
# ---------------------------------------------------------------------------

FETCHER_DEFS = [
    {
        "code": "API REST",
        "class_path": "app.fetchers.rest.RestFetcher",
        "description": "RESTful API with JSON/XML support",
        "params": [
            {"param_name": "url",         "data_type": "string",  "required": True},
            {"param_name": "method",      "data_type": "string",  "required": False, "default_value": "GET"},
            {"param_name": "timeout",     "data_type": "integer", "required": False, "default_value": 30},
            {"param_name": "max_retries", "data_type": "integer", "required": False, "default_value": 3},
        ],
    },
    {
        "code": "API REST Paginada",
        "class_path": "app.fetchers.paginated_rest.PaginatedRestFetcher",
        "description": "Paginated REST API — iterates pages until empty",
        "params": [
            {"param_name": "url",            "data_type": "string",  "required": True},
            {"param_name": "method",         "data_type": "string",  "required": False, "default_value": "GET"},
            {"param_name": "timeout",        "data_type": "integer", "required": False, "default_value": 60},
            {"param_name": "id_field",       "data_type": "string",  "required": False},
            {"param_name": "bounding_field", "data_type": "string",  "required": False},
        ],
    },
    {
        "code": "Feeds ATOM/RSS",
        "class_path": "app.fetchers.atom.AtomFetcher",
        "description": "ATOM/RSS feed reader",
        "params": [
            {"param_name": "url",       "data_type": "string",  "required": True},
            {"param_name": "max_items", "data_type": "integer", "required": False, "default_value": 1000},
        ],
    },
    {
        "code": "PLACSP Atom",
        "class_path": "app.fetchers.placsp_atom.PlacspAtomFetcher",
        "description": "PLACSP Atom paging feed with optional year/month filtering",
        "params": [
            {"param_name": "url",       "data_type": "string",  "required": True},
            {"param_name": "max_pages", "data_type": "integer", "required": False, "default_value": 100},
            {"param_name": "timeout",   "data_type": "integer", "required": False, "default_value": 60},
            {"param_name": "anio",      "data_type": "integer", "required": False},
            {"param_name": "mes",       "data_type": "integer", "required": False},
        ],
    },
    {
        "code": "File Download",
        "class_path": "app.fetchers.file_download.FileDownloadFetcher",
        "description": "Downloads a static file and converts rows to records. Supports XLSX, CSV and TSV.",
        "params": [
            {"param_name": "url",        "data_type": "string",  "required": True},
            {"param_name": "format",     "data_type": "string",  "required": True},
            {"param_name": "sheet",      "data_type": "string",  "required": False, "default_value": "0"},
            {"param_name": "skip_rows",  "data_type": "integer", "required": False, "default_value": 0},
            {"param_name": "delimiter",  "data_type": "string",  "required": False},
            {"param_name": "encoding",   "data_type": "string",  "required": False, "default_value": "utf-8-sig"},
            {"param_name": "columns",    "data_type": "json",    "required": False},
            {"param_name": "headers",    "data_type": "json",    "required": False},
            {"param_name": "batch_size", "data_type": "integer", "required": False, "default_value": 1000},
            {"param_name": "timeout",    "data_type": "integer", "required": False, "default_value": 60},
        ],
    },
    {
        "code": "Compressed File",
        "class_path": "app.fetchers.compressed_file.CompressedFileFetcher",
        "description": "Downloads a compressed archive (ZIP, TAR, TAR.GZ, TAR.BZ2, GZ) and parses the extracted file as CSV, TSV or XLSX.",
        "params": [
            {"param_name": "url",          "data_type": "string",  "required": True},
            {"param_name": "format",       "data_type": "string",  "required": True},
            {"param_name": "entry",        "data_type": "string",  "required": False},
            {"param_name": "inner_format", "data_type": "string",  "required": False},
            {"param_name": "skip_rows",    "data_type": "integer", "required": False, "default_value": 0},
            {"param_name": "delimiter",    "data_type": "string",  "required": False},
            {"param_name": "encoding",     "data_type": "string",  "required": False, "default_value": "utf-8-sig"},
            {"param_name": "sheet",        "data_type": "string",  "required": False, "default_value": "0"},
            {"param_name": "columns",      "data_type": "json",    "required": False},
            {"param_name": "headers",      "data_type": "json",    "required": False},
            {"param_name": "batch_size",   "data_type": "integer", "required": False, "default_value": 1000},
            {"param_name": "timeout",      "data_type": "integer", "required": False, "default_value": 120},
        ],
    },
    {
        "code": "HTML SearchLoop",
        "class_path": "app.fetchers.searchloop_html.SearchLoopHtmlFetcher",
        "description": "HTML scraper that pivots over <select> option values",
        "params": [
            {"param_name": "url",    "data_type": "string", "required": True},
            {"param_name": "levels", "data_type": "json",   "required": True},
        ],
    },
    {
        "code": "HTML Paginated",
        "class_path": "app.fetchers.paginated_html.PaginatedHtmlFetcher",
        "description": "HTML scraper with automatic pagination",
        "params": [
            {"param_name": "url",            "data_type": "string", "required": True},
            {"param_name": "row_selector",   "data_type": "string", "required": True},
            {"param_name": "next_selector",  "data_type": "string", "required": False},
        ],
    },
    {
        "code": "HTML Forms",
        "class_path": "app.fetchers.html.HtmlFetcher",
        "description": "Simple HTML form GET/POST scraper",
        "params": [
            {"param_name": "url",    "data_type": "string", "required": True},
            {"param_name": "method", "data_type": "string", "required": False, "default_value": "GET"},
        ],
    },
    {
        "code": "Portales CKAN",
        "class_path": "app.fetchers.ckan.CkanFetcher",
        "description": "CKAN open data portal API",
        "params": [
            {"param_name": "url",         "data_type": "string", "required": True},
            {"param_name": "resource_id", "data_type": "string", "required": True},
        ],
    },
    {
        "code": "OSM Overpass",
        "class_path": "app.fetchers.osm.OsmFetcher",
        "description": "OpenStreetMap Overpass API query",
        "params": [
            {"param_name": "query",   "data_type": "overpass_query", "required": True},
            {"param_name": "timeout", "data_type": "integer",        "required": False, "default_value": 120},
        ],
    },
    {
        "code": "WFS",
        "class_path": "app.fetchers.wfs.WFSFetcher",
        "description": "OGC Web Feature Service — vector features with automatic pagination",
        "params": [
            {"param_name": "endpoint",      "data_type": "string",  "required": True},
            {"param_name": "typenames",     "data_type": "string",  "required": True},
            {"param_name": "version",       "data_type": "string",  "required": False, "default_value": "2.0.0"},
            {"param_name": "outputFormat",  "data_type": "string",  "required": False, "default_value": "application/json"},
            {"param_name": "srsName",       "data_type": "string",  "required": False, "default_value": "EPSG:4326"},
            {"param_name": "bbox",          "data_type": "bbox",    "required": False},
            {"param_name": "cql_filter",    "data_type": "string",  "required": False},
            {"param_name": "count",         "data_type": "integer", "required": False, "default_value": 1000},
            {"param_name": "id_field",      "data_type": "string",  "required": False},
            {"param_name": "timeout",       "data_type": "integer", "required": False, "default_value": 120},
        ],
    },
    {
        "code": "WMS",
        "class_path": "app.fetchers.wms.WMSFetcher",
        "description": "OGC Web Map Service — map image metadata + URL",
        "params": [
            {"param_name": "endpoint",  "data_type": "string",  "required": True},
            {"param_name": "layers",    "data_type": "string",  "required": True},
            {"param_name": "bbox",      "data_type": "bbox",    "required": True},
            {"param_name": "version",   "data_type": "string",  "required": False, "default_value": "1.3.0"},
            {"param_name": "format",    "data_type": "string",  "required": False, "default_value": "image/png"},
            {"param_name": "crs",       "data_type": "string",  "required": False, "default_value": "EPSG:4326"},
            {"param_name": "styles",    "data_type": "string",  "required": False},
            {"param_name": "width",     "data_type": "integer", "required": False, "default_value": 1024},
            {"param_name": "height",    "data_type": "integer", "required": False, "default_value": 1024},
            {"param_name": "timeout",   "data_type": "integer", "required": False, "default_value": 120},
        ],
    },
    {
        "code": "Servicios SOAP/WSDL",
        "class_path": "app.fetchers.soap.SoapFetcher",
        "description": "SOAP/WSDL web service",
        "params": [
            {"param_name": "wsdl",      "data_type": "string", "required": True},
            {"param_name": "operation", "data_type": "string", "required": True},
        ],
    },
    {
        "code": "URL Loop HTML",
        "class_path": "app.fetchers.url_loop_html.UrlLoopHtmlFetcher",
        "description": (
            "HTML scraper genérico: pivota sobre una lista de valores, construye una URL por cada uno "
            "({value} en url_template), extrae múltiples registros por página mediante selectores CSS "
            "sobre texto, atributos o subelementos, y pagina automáticamente via un enlace next."
        ),
        "params": [
            # ── Grupo: URL ──────────────────────────────────────────────────────────
            {"param_name": "url_template",    "data_type": "string", "required": True,  "group": "url",
             "description": "Plantilla de URL. Usa {value} para el valor del pivot y {page} para el número de página. "
                            "Puede ser '{value}' si los valores del pivot ya son URLs completas."},
            {"param_name": "page_base_url",   "data_type": "string", "required": False, "group": "url",
             "description": "Host base para resolver hrefs relativos en la paginación (ej. 'https://example.com'). "
                            "Necesario cuando url_template es '{value}' y los enlaces de paginación son relativos."},
            # ── Grupo: Pivot estático ───────────────────────────────────────────────
            {"param_name": "pivot_values",    "data_type": "json",   "required": False, "group": "pivot_static",
             "description": "Lista JSON de valores sobre los que pivotar. Cada valor se sustituye en {value} de url_template. "
                            "Puede ser una lista de slugs, IDs, o URLs completas si url_template = '{value}'. "
                            "Alternativa: usar pivot dinámico desde ODMGR (ver grupo pivot_source)."},
            {"param_name": "pivot_field",     "data_type": "string", "required": False, "group": "pivot_static",
             "default_value": "pivot_value",
             "description": "Nombre del campo que se añade a cada registro con el valor del pivot actual."},
            # ── Grupo: Pivot dinámico ODMGR ────────────────────────────────────────
            {"param_name": "pivot_source_odmgr_query",  "data_type": "string", "required": False, "group": "pivot_source",
             "description": "Nombre de la query GraphQL del endpoint /graphql/data de ODMGR desde la que obtener "
                            "los valores del pivot. Formato camelCase del nombre del resource "
                            "(ej. 'agenciasInmobiliariasFotocasa'). Alternativa a pivot_values."},
            {"param_name": "pivot_source_field",        "data_type": "string", "required": False, "group": "pivot_source",
             "description": "Campo a extraer de cada registro del dataset ODMGR como valor del pivot "
                            "(ej. 'url_busqueda', 'provincia_id', 'codigo_ine')."},
            {"param_name": "pivot_source_odmgr_url",    "data_type": "string", "required": False, "group": "pivot_source",
             "description": "URL del endpoint GraphQL data de ODMGR. Por defecto usa la variable de entorno "
                            "ODMGR_DATA_URL o http://localhost:8000/graphql/data."},
            {"param_name": "pivot_source_filter_field", "data_type": "string", "required": False, "group": "pivot_source",
             "description": "Campo por el que filtrar los registros del dataset ODMGR (ej. 'fuente', 'activo')."},
            {"param_name": "pivot_source_filter_value", "data_type": "string", "required": False, "group": "pivot_source",
             "description": "Valor exacto del filtro sobre pivot_source_filter_field."},
            # ── Grupo: Extracción de registros ─────────────────────────────────────
            {"param_name": "record_selector",       "data_type": "string", "required": True,  "group": "extraction",
             "description": "Selector CSS del elemento raíz de cada registro en la página "
                            "(ej. 'article', 'tr.fila-dato', 'li[data-id]')."},
            {"param_name": "field_attrs",           "data_type": "json",   "required": False, "group": "extraction",
             "description": 'Extrae atributos del elemento raíz. JSON: {"campo": "nombre-atributo"} '
                            '(ej. {"id": "data-id", "nombre": "data-name"}).'},
            {"param_name": "field_selectors",       "data_type": "json",   "required": False, "group": "extraction",
             "description": 'Extrae el texto del primer subelemento que coincida. JSON: {"campo": "selector-css"} '
                            '(ej. {"precio": ".price span", "titulo": "h3"}).'},
            {"param_name": "field_attr_selectors",  "data_type": "json",   "required": False, "group": "extraction",
             "description": 'Extrae el atributo de un subelemento. JSON: {"campo": {"selector": "css", "attr": "atributo"}} '
                            '(ej. {"url": {"selector": "a.detail", "attr": "href"}}).'},
            {"param_name": "field_all_text",        "data_type": "json",   "required": False, "group": "extraction",
             "description": 'Concatena el texto de TODOS los subelementos que coincidan con el selector. '
                            'JSON: {"campo": "selector-css"} (ej. {"tags": "ul.tags li"}).'},
            {"param_name": "field_all_separator",   "data_type": "string", "required": False, "group": "extraction",
             "default_value": " | ",
             "description": "Separador usado al concatenar valores de field_all_text. Por defecto ' | '."},
            {"param_name": "required_field",        "data_type": "string", "required": False, "group": "extraction",
             "description": "Si se especifica, descarta los registros en los que este campo sea nulo o vacío. "
                            "Útil para filtrar artículos esqueleto/placeholder en páginas con lazy-loading."},
            # ── Grupo: Paginación ───────────────────────────────────────────────────
            {"param_name": "next_page_selector",  "data_type": "string",  "required": False, "group": "pagination",
             "description": "Selector CSS del enlace a la página siguiente. Si no se especifica no hay paginación. "
                            "(ej. 'a[rel=\"next\"]', 'a[aria-label=\"Página siguiente\"]')."},
            {"param_name": "next_page_attr",      "data_type": "string",  "required": False, "group": "pagination",
             "default_value": "href",
             "description": "Atributo del enlace de paginación del que extraer la URL (por defecto 'href')."},
            {"param_name": "max_pages",           "data_type": "integer", "required": False, "group": "pagination",
             "default_value": 500,
             "description": "Número máximo de páginas a recuperar por valor del pivot. "
                            "Límite de seguridad para evitar bucles infinitos."},
            {"param_name": "delay_between_pages", "data_type": "number",  "required": False, "group": "pagination",
             "default_value": 1.5,
             "description": "Segundos de espera entre páginas consecutivas del mismo pivot. "
                            "Reduce la carga sobre el servidor origen."},
            # ── Grupo: Comportamiento ───────────────────────────────────────────────
            {"param_name": "delay_between_pivots","data_type": "number",  "required": False, "group": "behavior",
             "default_value": 2.0,
             "description": "Segundos de espera al pasar al siguiente valor del pivot."},
            {"param_name": "stop_on_error",       "data_type": "boolean", "required": False, "group": "behavior",
             "default_value": False,
             "description": "Si es true, detiene la ejecución al primer error HTTP de un pivot. "
                            "Si es false (defecto), registra el error y continúa con el siguiente."},
            {"param_name": "headers",             "data_type": "json",    "required": False, "group": "behavior",
             "description": "Cabeceras HTTP adicionales en formato JSON. Se fusionan con las cabeceras por defecto "
                            "(User-Agent Chrome, Accept HTML, Accept-Language es-ES). "
                            'Ej: {"Cookie": "session=abc", "Referer": "https://example.com"}.'},
            {"param_name": "timeout",             "data_type": "integer", "required": False, "group": "behavior",
             "default_value": 30,
             "description": "Timeout HTTP en segundos para cada petición."},
        ],
    },
    {
        "code": "REST Loop",
        "class_path": "app.fetchers.rest_loop.RestLoopFetcher",
        "description": "REST API iterated over a list of pivot values (e.g. province codes)",
        "params": [
            {"param_name": "url",              "data_type": "string",  "required": True},
            {"param_name": "method",           "data_type": "string",  "required": False, "default_value": "POST"},
            {"param_name": "payload_template", "data_type": "json",    "required": False},
            {"param_name": "pivot_values",     "data_type": "json",    "required": False},
            {"param_name": "id_field",         "data_type": "string",  "required": False},
            {"param_name": "delay",            "data_type": "number",  "required": False, "default_value": 2},
            {"param_name": "timeout",          "data_type": "integer", "required": False, "default_value": 30},
            {"param_name": "headers",          "data_type": "json",    "required": False},
        ],
    },
    {
        "code": "JSON Time Series",
        "class_path": "app.fetchers.json_timeseries.JsonTimeseriesFetcher",
        "description": (
            "Generic fetcher for APIs that return arrays of time series with metadata. "
            "Flattens nested structure (series → metadata dimensions + data points) "
            "into tabular records. Configurable for any stats API with this pattern."
        ),
        "params": [
            # HTTP
            {"param_name": "url",             "data_type": "string",  "required": True,
             "group": "http", "description": "API endpoint URL"},
            {"param_name": "method",          "data_type": "string",  "required": False, "default_value": "GET",
             "group": "http"},
            {"param_name": "query_params",    "data_type": "json",    "required": False,
             "group": "http", "description": "Query string params as JSON object"},
            {"param_name": "headers",         "data_type": "json",    "required": False,
             "group": "http"},
            {"param_name": "timeout",         "data_type": "integer", "required": False, "default_value": 120,
             "group": "http"},
            # Response structure
            {"param_name": "root_path",       "data_type": "string",  "required": False,
             "group": "structure", "description": "Dot-path to the root array in the response. Empty = response IS the array"},
            {"param_name": "meta_container",  "data_type": "string",  "required": False, "default_value": "MetaData",
             "group": "structure", "description": "Key of the metadata array in each series element"},
            {"param_name": "meta_code_field", "data_type": "string",  "required": False, "default_value": "Codigo",
             "group": "structure"},
            {"param_name": "meta_name_field", "data_type": "string",  "required": False, "default_value": "Nombre",
             "group": "structure"},
            {"param_name": "meta_dim_path",   "data_type": "string",  "required": False, "default_value": "Variable.Codigo",
             "group": "structure", "description": "Dot-path to the dimension name within each metadata item"},
            {"param_name": "data_container",  "data_type": "string",  "required": False, "default_value": "Data",
             "group": "structure", "description": "Key of the data-points array in each series element"},
            {"param_name": "period_field",    "data_type": "string",  "required": False, "default_value": "Anyo",
             "group": "structure"},
            {"param_name": "subperiod_field", "data_type": "string",  "required": False, "default_value": "Periodo",
             "group": "structure"},
            {"param_name": "value_field",     "data_type": "string",  "required": False, "default_value": "Valor",
             "group": "structure"},
            {"param_name": "secret_field",    "data_type": "string",  "required": False, "default_value": "Secreto",
             "group": "structure", "description": "Boolean field to skip suppressed data. Empty to disable"},
            {"param_name": "serie_name_field","data_type": "string",  "required": False, "default_value": "Nombre",
             "group": "structure"},
            # Output
            {"param_name": "flatten_mode",   "data_type": "string",  "required": False, "default_value": "long",
             "group": "output", "description": "long: one row per (series × period). wide: one row per series"},
            {"param_name": "batch_size",     "data_type": "integer", "required": False, "default_value": 500,
             "group": "output"},
        ],
    },
    {
        "code": "XBRL ZIP",
        "class_path": "app.fetchers.xbrl.XbrlFetcher",
        "description": (
            "Generic fetcher for ZIP archives containing XBRL documents (XML-based financial/accounting standard). "
            "Extracts numeric elements with their period contexts into tabular records. "
            "Suitable for any source publishing XBRL: Tribunal de Cuentas, CNMV, Banco de España, SEC, etc."
        ),
        "params": [
            # HTTP
            {"param_name": "url",            "data_type": "string",  "required": True,
             "group": "http", "description": "URL of the ZIP file containing XBRL documents"},
            {"param_name": "method",         "data_type": "string",  "required": False, "default_value": "GET",
             "group": "http"},
            {"param_name": "query_params",   "data_type": "json",    "required": False,
             "group": "http", "description": "Query string params as JSON, e.g. {\"nif\":\"P1102900A\",\"ejercicio\":\"2023\"}"},
            {"param_name": "headers",        "data_type": "json",    "required": False,
             "group": "http"},
            {"param_name": "timeout",        "data_type": "integer", "required": False, "default_value": 120,
             "group": "http"},
            # ZIP contents
            {"param_name": "xml_pattern",    "data_type": "string",  "required": False,
             "group": "zip", "description": "Glob pattern to filter XML files inside the ZIP. Empty = all .xml"},
            {"param_name": "entry",          "data_type": "string",  "required": False,
             "group": "zip", "description": "Exact filename of a single XML to process"},
            {"param_name": "file_classifier","data_type": "json",    "required": False,
             "group": "zip", "description": "JSON map: keyword → label for classifying XML files into 'estado_contable'"},
            # Record enrichment
            {"param_name": "context_fields", "data_type": "json",    "required": False,
             "group": "output", "description": "JSON map of fixed fields added to every record, e.g. {\"nif_entidad\":\"P1102900A\"}"},
            {"param_name": "account_prefix", "data_type": "string",  "required": False,
             "group": "output", "description": "Comma-separated tag prefixes to include. Empty = all numeric elements"},
            {"param_name": "exclude_tags",   "data_type": "string",  "required": False,
             "group": "output", "description": "Comma-separated XBRL infrastructure tags to skip"},
            {"param_name": "batch_size",     "data_type": "integer", "required": False, "default_value": 200,
             "group": "output"},
        ],
    },
]


# ---------------------------------------------------------------------------
# 2. PUBLISHERS
# ---------------------------------------------------------------------------

PUBLISHER_DEFS = [
    {
        "acronimo": "MPTFP",
        "nombre":   "Secretaría de Estado de Función Pública",
        "nivel":    "ESTATAL",
        "pais":     "España",
        "portal_url": "https://administracionelectronica.gob.es",
    },
    {
        "acronimo": "INE",
        "nombre":   "Instituto Nacional de Estadística",
        "nivel":    "ESTATAL",
        "pais":     "España",
        "portal_url": "https://www.ine.es",
    },
    {
        "acronimo": "MINHAC",
        "nombre":   "Ministerio de Hacienda",
        "nivel":    "ESTATAL",
        "pais":     "España",
        "portal_url": "https://www.hacienda.gob.es",
    },
    {
        "acronimo": "PLACSP",
        "nombre":   "Plataforma de Contratación del Sector Público",
        "nivel":    "ESTATAL",
        "pais":     "España",
        "portal_url": "https://contrataciondelestado.es",
    },
    {
        "acronimo": "IGAE",
        "nombre":   "Intervención General de la Administración del Estado",
        "nivel":    "ESTATAL",
        "pais":     "España",
        "portal_url": "https://www.igae.pap.hacienda.gob.es",
    },
    {
        "acronimo": "MJUST",
        "nombre":   "Ministerio de Justicia",
        "nivel":    "ESTATAL",
        "pais":     "España",
        "portal_url": "https://www.mjusticia.gob.es",
    },
    {
        "acronimo": "FGE",
        "nombre":   "Fiscalía General del Estado",
        "nivel":    "ESTATAL",
        "pais":     "España",
        "portal_url": "https://www.fiscalia.es",
    },
    {
        "acronimo": "CGN",
        "nombre":   "Consejo General del Notariado",
        "nivel":    "ESTATAL",
        "pais":     "España",
        "portal_url": "https://www.notariado.org",
    },
    {
        "acronimo": "DGC",
        "nombre":   "Dirección General del Catastro",
        "nivel":    "ESTATAL",
        "pais":     "España",
        "portal_url": "https://www.catastro.meh.es",
    },
    {
        "acronimo": "JDA",
        "nombre":   "Junta de Andalucía",
        "nivel":    "AUTONOMICO",
        "pais":     "España",
        "comunidad_autonoma": "Andalucía",
        "portal_url": "https://www.juntadeandalucia.es",
    },
    {
        "acronimo": "BDNS",
        "nombre":   "Base de Datos Nacional de Subvenciones",
        "nivel":    "ESTATAL",
        "pais":     "España",
        "portal_url": "https://www.infosubvenciones.es",
    },
    {
        "acronimo": "CORPME",
        "nombre":   "Colegio de Registradores de la Propiedad, Bienes Muebles y Mercantiles de España",
        "nivel":    "ESTATAL",
        "pais":     "España",
        "portal_url": "https://www.registradores.org",
    },
    {
        "acronimo": "CSCAE",
        "nombre":   "Consejo Superior de los Colegios de Arquitectos de España",
        "nivel":    "ESTATAL",
        "pais":     "España",
        "portal_url": "https://www.cscae.com",
    },
    {
        "acronimo": "CGATE",
        "nombre":   "Consejo General de la Arquitectura Técnica de España",
        "nivel":    "ESTATAL",
        "pais":     "España",
        "portal_url": "https://www.cgate.es",
    },
    {
        "acronimo": "CEE",
        "nombre":   "Conferencia Episcopal Española",
        "nivel":    "ESTATAL",
        "pais":     "España",
        "portal_url": "https://www.conferenciaepiscopal.es",
    },
    {
        "acronimo": "FOTOCASA",
        "nombre":   "Fotocasa (Schibsted Spain)",
        "nivel":    "PRIVADO",
        "pais":     "España",
        "portal_url": "https://www.fotocasa.es",
    },
    {
        "acronimo": "SEPE",
        "nombre":   "Servicio Público de Empleo Estatal",
        "nivel":    "ESTATAL",
        "pais":     "España",
        "portal_url": "https://sede.sepe.gob.es",
    },
    {
        "acronimo": "TRIBUCON",
        "nombre":   "Tribunal de Cuentas",
        "nivel":    "ESTATAL",
        "pais":     "España",
        "portal_url": "https://www.rendiciondecuentas.es",
    },
    {
        "acronimo": "MINHAC-EL",
        "nombre":   "Ministerio de Hacienda — Entidades Locales",
        "nivel":    "ESTATAL",
        "pais":     "España",
        "portal_url": "https://serviciostelematicosext.hacienda.gob.es",
    },
]


# ---------------------------------------------------------------------------
# 3. FOUNDATION RESOURCES
# ---------------------------------------------------------------------------
# These are reference datasets the application itself depends on.
# Listed as (name, fetcher_code, publisher_acronimo, target_table, params_dict, schedule)

RESOURCE_DEFS = [
    {
        "name":             "DIR3 - Unidades Orgánicas de España",
        "fetcher_code":     "API REST",
        "publisher_acronimo": "JDA",
        "target_table":     "dir3_unidades",
        "schedule":         "0 3 * * 0",   # weekly, Sunday 03:00
        "params": {
            "url":             "https://datos.juntadeandalucia.es/api/v0/dir3/all?format=json",
            "method":          "GET",
            "timeout":         "120",
            "id_field":        "id",
        },
    },
    {
        "name":             "España - Municipios (INE)",
        "fetcher_code":     "File Download",
        "publisher_acronimo": "INE",
        "target_table":     "geo_municipios",
        "schedule":         "0 4 1 1 *",   # yearly, 1 Jan 04:00
        # URL uses 2-digit year suffix (e.g. 26codmun.xlsx for 2026). Update annually.
        "params": {
            "url":       "https://www.ine.es/daco/daco42/codmun/26codmun.xlsx",
            "format":    "xlsx",
            "skip_rows": "2",   # INE header occupies rows 0-1; data starts at row 2
            "timeout":   "60",
            "headers":   '{"User-Agent": "Mozilla/5.0", "Referer": "https://www.ine.es/"}',
        },
    },
    {
        "name":             "España - Provincias (INE)",
        "fetcher_code":     "API REST",
        "publisher_acronimo": "INE",
        "target_table":     "geo_provincias",
        "schedule":         "0 4 1 1 *",   # yearly, 1 Jan 04:00
        # VALORES_VARIABLE/20: 52 provincias con Id interno, Codigo (2 dig), Nombre,
        # FK_JerarquiaPadres[0].Id -> Id interno de la CCAA padre
        "params": {
            "url":     "https://servicios.ine.es/wstempus/js/ES/VALORES_VARIABLE/20",
            "method":  "GET",
            "timeout": "60",
        },
    },
    {
        "name":             "España - Comunidades Autónomas (INE)",
        "fetcher_code":     "API REST",
        "publisher_acronimo": "INE",
        "target_table":     "geo_ccaa",
        "schedule":         "0 4 1 1 *",   # yearly, 1 Jan 04:00
        # VALORES_VARIABLE/70: 19 CCAA con Id interno, Codigo (2 dig), Nombre
        "params": {
            "url":     "https://servicios.ine.es/wstempus/js/ES/VALORES_VARIABLE/70",
            "method":  "GET",
            "timeout": "60",
        },
    },
    {
        "name":             "FACE - Relaciones OC/OG/UT (Nacional)",
        "fetcher_code":     "API REST Paginada",
        "publisher_acronimo": "MPTFP",
        "target_table":     "face_relations",
        "schedule":         "0 4 * * 0",   # weekly, Sunday 04:00
        "params": {
            "url":            "https://proveedores.face.gob.es/api/v1/relations",
            "method":         "GET",
            "timeout":        "60",
            "page_param":     "page",
            "page_size_param": "limit",
            "page_size":      "1000",
            "content_field":  "items",
            "id_field":       "",           # no dedup — dedup done at search time
            "headers":        '{"User-Agent": "Python/requests", "Accept": "application/json"}',
            "page_start":     "1",
        },
    },
    {
        "name":             "Notarías - Guía Notarial (CGN)",
        "fetcher_code":     "REST Loop",
        "publisher_acronimo": "CGN",
        "target_table":     "notarios",
        "schedule":         "0 2 * * 0",   # weekly, Sunday 02:00
        "params": {
            "url":     "https://guianotarial.notariado.org/guianotarial/rest/buscar/notarios",
            "method":  "POST",
            "payload_template": '{"nombre":"","apellidos":"","direccion":"","codigoPostal":"","codigoProvincia":"{pivot}","municipio":"","codigoSituacionNotario":"","idiomaExtranjero":""}',
            "id_field": "codigoNotaria",
            "delay":    "3",
            "timeout":  "60",
        },
    },
    {
        "name":               "Catastro - Parcelas (Sevilla)",
        "fetcher_code":       "WFS",
        "publisher_acronimo": "DGC",
        "target_table":       "catastro_parcelas",
        "schedule":           "0 3 1 * *",
        "params": {
            "endpoint":      "http://ovc.catastro.meh.es/INSPIRE/wfsCP.aspx",
            "typenames":     "cp:CadastralParcel",
            "bbox":          "-6.4,36.9,-5.3,37.9",
            "outputFormat":  "application/gml+xml; version=3.2",
            "srsName":       "EPSG:4326",
            "count":         "500",
            "id_field":      "nationalCadastralReference",
            "timeout":       "120",
        },
    },
    {
        "name":               "OSM - Inmuebles Eclesiásticos (España)",
        "fetcher_code":       "OSM Overpass",
        "publisher_acronimo": None,   # dato de OSM community, sin publisher institucional
        "target_table":       "osm_inmuebles_eclesiasticos",
        "schedule":           "0 2 * * 0",   # weekly, Sunday 02:00
        "params": {
            # Presets RELIGIOUS_ALL + RELIGIOUS_BUILDING_EXTRA cubren:
            # iglesias, catedrales, basílicas, capillas, monasterios, conventos,
            # ermitas, cruces, humilladeros, grottas de Lourdes — con y sin denominación
            "use_types":      '[{"preset": "RELIGIOUS_ALL"}, {"preset": "RELIGIOUS_BUILDING_EXTRA"}]',
            "demarcacion":    "España",
            "element_types":  "node,way,relation",
            "out_format":     "center",
            "timeout":        "1800",
            "max_elements":   "0",
        },
    },
    {
        "name":               "BDNS - Concesiones de Subvenciones",
        "fetcher_code":       "API REST Paginada",
        "publisher_acronimo": "BDNS",
        "target_table":       "bdns_concesiones",
        "schedule":           "0 4 * * 1",   # weekly, Monday 04:00
        "params": {
            "url":            "https://www.infosubvenciones.es/bdnstrans/api/concesiones/busqueda",
            "page_param":     "page",
            "page_size_param": "pageSize",
            "page_size":      "10000",
            "content_field":  "content",
            "id_field":       "id",
            # External (runtime-overridable) — date range in DD/MM/YYYY
            "fechaDesde":     {"value": "01/01/2026", "is_external": True},
            "fechaHasta":     {"value": "31/12/2026", "is_external": True},
        },
    },
    {
        "name":               "BDNS - Convocatorias de Subvenciones",
        "fetcher_code":       "API REST Paginada",
        "publisher_acronimo": "BDNS",
        "target_table":       "bdns_grants",
        "schedule":           "0 3 * * 1",   # weekly, Monday 03:00
        "params": {
            "url":            "https://www.infosubvenciones.es/bdnstrans/api/convocatorias/busqueda",
            "method":         "get",
            "page_param":     "page",
            "page_size_param": "pageSize",
            "page_size":      "10000",
            "content_field":  "content",
            "id_field":       "id",
            "timeout":        "60",
            "query_params":   '{"page": "0", "pageSize": "100", "order": "numeroConvocatoria", "direccion": "desc", "vpd": "GE"}',
            # External (runtime-overridable) — date range in DD/MM/YYYY
            "fechaDesde":     {"value": "01/01/2026", "is_external": True},
            "fechaHasta":     {"value": "31/12/2026", "is_external": True},
        },
    },
    # ── SIPI: Agentes poblables por ETL ──────────────────────────────────────
    {
        "name":               "Registros de la Propiedad (CORPME)",
        "fetcher_code":       "File Download",
        "publisher_acronimo": "CORPME",
        "target_table":       "registros_propiedad",
        "schedule":           "0 3 1 * *",   # mensual, día 1 a las 03:00
        # CORPME publica el listado oficial en XLSX desde su portal de estadística.
        # El fichero contiene: Número de Registro, Denominación, Municipio, Provincia,
        # Dirección, CP, Teléfono, Fax, Email, URL.
        "params": {
            "url":       "https://www.registradores.org/documents/20122/573720/Listado_Registros_Propiedad.xlsx",
            "format":    "xlsx",
            "skip_rows": "1",
            "timeout":   "60",
            "headers":   '{"User-Agent": "Mozilla/5.0", "Referer": "https://www.registradores.org/"}',
        },
    },
    {
        "name":               "Agencias Inmobiliarias (Fotocasa)",
        "fetcher_code":       "URL Loop HTML",
        "publisher_acronimo": "FOTOCASA",
        "target_table":       "agencias_inmobiliarias",
        "schedule":           "0 2 1 * *",   # mensual, día 1 a las 02:00
        # Scraper del directorio https://www.fotocasa.es/buscar-agencias-inmobiliarias/
        # Las 52 provincias como pivot. Paginación via rel="next".
        # agency_id (= clientId de Fotocasa) es la clave idempotente para detectar
        # altas y bajas entre ejecuciones. Una misma cadena de agencias aparece
        # en múltiples provincias — el ETL agrupa por agency_id.
        "params": {
            "url_template":    "https://www.fotocasa.es/buscar-agencias-inmobiliarias/{value}/todas-las-zonas/l",
            "pivot_values":    (
                '["a-coruna-provincia","albacete-provincia","alicante-provincia",'
                '"almeria-provincia","araba-alava-provincia","asturias-provincia",'
                '"avila-provincia","badajoz-provincia","barcelona-provincia",'
                '"bizkaia-provincia","burgos-provincia","caceres-provincia",'
                '"cadiz-provincia","cantabria-provincia","castellon-provincia",'
                '"ceuta-provincia","ciudad-real-provincia","cordoba-provincia",'
                '"cuenca-provincia","gipuzkoa-provincia","girona-provincia",'
                '"granada-provincia","guadalajara-provincia","huelva-provincia",'
                '"huesca-provincia","illes-balears-provincia","jaen-provincia",'
                '"la-rioja-provincia","las-palmas-provincia","leon-provincia",'
                '"lleida-provincia","lugo-provincia","madrid-provincia",'
                '"malaga-provincia","melilla-provincia","murcia-provincia",'
                '"navarra-provincia","ourense-provincia","palencia-provincia",'
                '"pontevedra-provincia","salamanca-provincia",'
                '"santa-cruz-de-tenerife-provincia","segovia-provincia",'
                '"sevilla-provincia","soria-provincia","tarragona-provincia",'
                '"teruel-provincia","toledo-provincia","valencia-provincia",'
                '"valladolid-provincia","zamora-provincia","zaragoza-provincia"]'
            ),
            "record_selector":       "article[data-agency-id]",
            "field_attrs":           '{"agency_id": "data-agency-id", "nombre": "data-agency-name"}',
            "field_attr_selectors":  '{"url_busqueda": {"selector": "button[data-promiseref]", "attr": "data-promiseref"}}',
            "field_all_text":        '{"estadisticas": ".re-description-item label"}',
            "next_page_selector":    'a[rel="next"]',
            "pivot_field":           "provincia",
            "delay_between_pages":   "1.5",
            "delay_between_pivots":  "2.0",
            "max_pages":             "500",
            "timeout":               "30",
        },
    },
    # CSCAE (Colegios de Arquitectos) y CGATE (Aparejadores) no exponen APIs JSON públicas.
    # Sus directorios de colegios son páginas HTML estáticas sin endpoint de datos.
    # Pendiente: cargar manualmente o buscar fuente alternativa verificada.
    # {
    #     "name": "Colegios de Arquitectos (CSCAE)",
    #     ...  # sin API pública verificada a 2026-04
    # },
    # {
    #     "name": "Colegios de Aparejadores y Arquitectos Técnicos (CGATE)",
    #     ...  # sin API pública verificada a 2026-04
    # },
    {
        "name":               "Agencias Inmobiliarias (RERA Andalucía)",
        "fetcher_code":       "API REST Paginada",
        "publisher_acronimo": "JDA",
        "target_table":       "agencias_inmobiliarias",
        "schedule":           "0 4 * * 0",   # semanal, domingos 04:00
        # Registro de Agentes Inmobiliarios de Andalucía (RERA).
        # CKAN datastore API — datos.juntadeandalucia.es
        # El resource_id puede variar; verificar en:
        # https://datos.juntadeandalucia.es/dataset/rera-registro-de-agentes-inmobiliarios
        "params": {
            "url":             "https://datos.juntadeandalucia.es/api/action/datastore_search",
            "method":          "GET",
            "page_param":      "offset",
            "page_size_param": "limit",
            "page_size":       "1000",
            "content_field":   "result.records",
            "id_field":        "_id",
            "timeout":         "60",
            "resource_id":     {"value": "d84a2543-e94b-4d9e-854b-58e4d0b7db38", "is_external": True},
        },
    },
    {
        "name":               "Diócesis y Entidades Religiosas (CEE)",
        "fetcher_code":       "File Download",
        "publisher_acronimo": "CEE",
        "target_table":       "entidades_religiosas",
        "schedule":           "0 3 1 1 *",   # anual, 1 enero
        # La CEE publica el directorio de diócesis y archidiócesis en su web.
        # Fichero XLSX con: nombre, tipo (diócesis/archidiócesis/prelatura),
        # obispo, sede, municipio, provincia, teléfono, web.
        "params": {
            "url":       "https://www.conferenciaepiscopal.es/data/diocesis.xlsx",
            "format":    "xlsx",
            "skip_rows": "1",
            "timeout":   "30",
            "headers":   '{"User-Agent": "Mozilla/5.0"}',
        },
    },
    {
        "name":               "Oferta Inmobiliaria en Venta (Fotocasa)",
        "fetcher_code":       "URL Loop HTML",
        "publisher_acronimo": "FOTOCASA",
        "target_table":       "fotocasa_inmuebles",
        "schedule":           "0 3 * * 1",   # semanal, lunes 03:00
        # Scraper de inmuebles en venta pivotando sobre URLs de agencia.
        #
        # ESTRATEGIA (dos pasos):
        #   1. Ejecutar "Agencias Inmobiliarias (Fotocasa)" → rellena staging agencias_inmobiliarias
        #      + agencias_provincias (campo url_busqueda por agencia × provincia).
        #   2. Este recurso pivota sobre esas url_busqueda:
        #        url_template = "{value}"   ← el value ya ES la URL completa
        #        pivot_values = lista de url_busqueda desde staging agencias_provincias
        #
        # Cada url_busqueda es del tipo:
        #   /es/inmobiliaria-{slug}/comprar/inmuebles/{provincia}/todas-las-zonas/l?clientId={id}
        # Las páginas de agencia tienen SSR completo (15-30 inmuebles por página);
        # las páginas de búsqueda provincial NO (solo 1 artículo SSR, resto lazy-loaded).
        #
        # PIVOT_VALUES: poblar a partir de ODMGR staging tras ejecutar el paso 1:
        #   SELECT url_busqueda FROM staging.agencias_provincias WHERE url_busqueda IS NOT NULL
        # Los valores por defecto son URLs de demo (IKESA Sevilla) para test/preview.
        #
        # Clave idempotente: property_id extraído del url_path (penúltimo segmento).
        # Un mismo inmueble puede aparecer en varias agencias; el ETL deduplica por id.
        #
        # Campos extraídos:
        #   url_path       → href de h3 > a  (ej. /es/comprar/vivienda/sevilla/.../186033299/d)
        #   precio         → span en contenedor [class*=text-display-3]
        #   titulo         → texto del h3
        #   municipio      → p[class*=opacity-75]
        #   caracteristicas→ ul[class*=text-body-1] li (habs, baños, m², extras)
        #   agencia_url    → href logo agencia — contiene ?clientId=  (fuente del pivot)
        #   agencia_nombre → alt del img del logo (ej. "Inmuebles IKESA")
        "params": {
            # url_template = "{value}" → el pivot_value es la URL completa de cada agencia×provincia.
            "url_template":    "{value}",
            "page_base_url":   "https://www.fotocasa.es",
            # Pivot dinámico: lee url_busqueda del staging de agencias (paso previo).
            # Requiere que "Agencias Inmobiliarias (Fotocasa)" se haya ejecutado antes.
            # Si el staging está vacío o no existe, usar pivot_values como fallback de demo.
            "pivot_source_odmgr_query": "agenciasInmobiliariasFotocasa",
            "pivot_source_field":       "url_busqueda",
            # Fallback / demo (2 agencias Sevilla) mientras no hay staging de agencias.
            # Eliminar o vaciar una vez que el paso 1 haya corrido.
            "pivot_values":    (
                '["https://www.fotocasa.es/es/inmobiliaria-ikesa/comprar/inmuebles/sevilla-provincia/todas-las-zonas/l?clientId=9202760540246",'
                ' "https://www.fotocasa.es/es/inmobiliaria-winning-properties/comprar/inmuebles/sevilla-provincia/todas-las-zonas/l?clientId=9202751942277"]'
            ),
            "pivot_field":           "agencia_provincia_url",
            "record_selector":       "article",
            "field_attr_selectors":  (
                '{"url_path":        {"selector": "h3 a",                                        "attr": "href"},'
                ' "agencia_url":     {"selector": "a[data-panot-component=\'link-box-raised\']", "attr": "href"},'
                ' "agencia_nombre":  {"selector": "a[data-panot-component=\'link-box-raised\'] img", "attr": "alt"}}'
            ),
            "field_selectors":       (
                '{"precio":    "[class*=\'text-display-3\'] span",'
                ' "titulo":    "h3",'
                ' "municipio": "p[class*=\'opacity-75\']"}'
            ),
            "field_all_text":        '{"caracteristicas": "ul[class*=\'text-body-1\'] li"}',
            "next_page_selector":    'a[aria-label="Página siguiente"]',
            "required_field":        "url_path",   # filtra artículos esqueleto sin datos reales
            "delay_between_pages":   "2.0",
            "delay_between_pivots":  "5.0",
            "max_pages":             "500",
            "timeout":               "30",
        },
    },
    # ── Socioeconomía municipal ───────────────────────────────────────────────
    {
        "name":               "INE - Padrón Municipal (todos los municipios)",
        "fetcher_code":       "JSON Time Series",
        "publisher_acronimo": "INE",
        "target_table":       "ine_padron_municipal",
        "schedule":           "0 5 15 6 *",   # yearly, 15 Jun 05:00 (INE publica en mayo-junio)
        # Tabla 2852: Población residente por municipio, sexo y año.
        # Devuelve una serie por cada combinación (municipio × sexo).
        # Con nult=10 obtenemos los últimos 10 años de todos los municipios de España.
        # MetaData: [{Variable.Codigo: "SEX", Codigo: "T/H/M"}, {Variable.Codigo: "MUN", Codigo: "11020"}]
        # Data: [{Anyo: 2023, Periodo: "1", Valor: 213219}]
        "params": {
            "url":             "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/2852",
            "query_params":    '{"nult": "10", "det": "2"}',
            "headers":         '{"User-Agent": "Mozilla/5.0 (OpenDataManager/1.0; +https://github.com/PepeluiMoreno)"}',
            "timeout":         "180",
            # Estructura de respuesta INE
            "meta_container":  "MetaData",
            "meta_code_field": "Codigo",
            "meta_name_field": "Nombre",
            "meta_dim_path":   "Variable.Codigo",
            "data_container":  "Data",
            "period_field":    "Anyo",
            "subperiod_field": "",
            "value_field":     "Valor",
            "secret_field":    "Secreto",
            "serie_name_field": "Nombre",
            "flatten_mode":    "long",
            "batch_size":      "1000",
        },
    },
    {
        "name":               "INE - Atlas de Distribución de Renta (municipios)",
        "fetcher_code":       "JSON Time Series",
        "publisher_acronimo": "INE",
        "target_table":       "ine_renta_municipal",
        "schedule":           "0 5 1 11 *",   # yearly, 1 Nov 05:00 (INE publica en oct-nov)
        # Tabla 30896: Renta neta media por persona y unidad de consumo, por municipio.
        # Periodicidad anual. Cobertura: municipios ≥ 1000 hab. (incluye Jerez y grupo comparación).
        # MetaData: [{Variable.Codigo: "MUN"}, {Variable.Codigo: "TRENTA"} (tipo de renta)]
        "params": {
            "url":             "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/30896",
            "query_params":    '{"nult": "8", "det": "2"}',
            "headers":         '{"User-Agent": "Mozilla/5.0 (OpenDataManager/1.0)"}',
            "timeout":         "180",
            "meta_container":  "MetaData",
            "meta_code_field": "Codigo",
            "meta_name_field": "Nombre",
            "meta_dim_path":   "Variable.Codigo",
            "data_container":  "Data",
            "period_field":    "Anyo",
            "subperiod_field": "",
            "value_field":     "Valor",
            "secret_field":    "Secreto",
            "serie_name_field": "Nombre",
            "flatten_mode":    "long",
            "batch_size":      "500",
        },
    },
    {
        "name":               "INE - Encuesta Ocupación Hotelera (municipios)",
        "fetcher_code":       "JSON Time Series",
        "publisher_acronimo": "INE",
        "target_table":       "ine_eoh_municipal",
        "schedule":           "0 6 25 * *",   # monthly, day 25 06:00 (INE publica ~día 23)
        # Tabla 2066: Viajeros y pernoctaciones en establecimientos hoteleros por municipio.
        # Periodicidad mensual. Útil para municipios turísticos como Jerez.
        # MetaData: [{Variable.Codigo: "MUN"}, {Variable.Codigo: "TRESI"} (residencia viajero)]
        "params": {
            "url":             "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/2066",
            "query_params":    '{"nult": "24", "det": "2"}',
            "headers":         '{"User-Agent": "Mozilla/5.0 (OpenDataManager/1.0)"}',
            "timeout":         "180",
            "meta_container":  "MetaData",
            "meta_code_field": "Codigo",
            "meta_name_field": "Nombre",
            "meta_dim_path":   "Variable.Codigo",
            "data_container":  "Data",
            "period_field":    "Anyo",
            "subperiod_field": "Periodo",
            "value_field":     "Valor",
            "secret_field":    "Secreto",
            "serie_name_field": "Nombre",
            "flatten_mode":    "long",
            "batch_size":      "500",
        },
    },
    {
        "name":               "SEPE - Paro Registrado por Municipio",
        "fetcher_code":       "File Download",
        "publisher_acronimo": "SEPE",
        "target_table":       "sepe_paro_municipal",
        "schedule":           "0 7 10 1 *",  # anual, 1 enero 07:10 — SEPE publica CSV anual consolidado
        # SEPE publica un CSV anual con paro registrado por municipio.
        # URL patrón: https://sede.sepe.gob.es/es/portaltrabaja/resources/sede/datos_abiertos/datos/Paro_por_municipios_{YYYY}_csv.csv
        # El año activo se parametriza en el Resource (is_external=True)
        # CSV: cod_municipio, nom_municipio, total_paro, hombres, mujeres,
        #       sector_agricultura, sector_industria, sector_construccion,
        #       sector_servicios, sector_sin_empleo_anterior
        "params": {
            "url":       {"value": "https://sede.sepe.gob.es/es/portaltrabaja/resources/sede/datos_abiertos/datos/Paro_por_municipios_2025_csv.csv", "is_external": True},
            "format":    "csv",
            "encoding":  "latin-1",
            "delimiter": ";",
            "timeout":   "120",
            "headers":   '{"User-Agent": "Mozilla/5.0 (OpenDataManager/1.0)"}',
        },
    },
    {
        "name":               "Hacienda - Periodo Medio de Pago (Entidades Locales)",
        "fetcher_code":       "File Download",
        "publisher_acronimo": "MINHAC-EL",
        "target_table":       "hacienda_pmp_el",
        "schedule":           "0 7 20 * *",   # monthly, day 20 07:00 (Hacienda publica ~días 15-18)
        # Ministerio de Hacienda publica mensualmente el PMP de todas las entidades locales.
        # CSV con: entidad, tipo_entidad, periodo, pmp_proveedores,
        #          operaciones_pagadas_euros, operaciones_pendientes_euros
        # URL patrón: .../PMPEL_AAAAMM.csv (el mes se actualiza vía is_external)
        "params": {
            "url":      {"value": "https://serviciostelematicosext.hacienda.gob.es/SGFAL/CONPREL/pmp/PMPEL_202503.csv", "is_external": True},
            "format":   "csv",
            "encoding": "utf-8-sig",
            "delimiter": ";",
            "timeout":  "60",
        },
    },
    {
        "name":               "Hacienda - Deuda Viva de los Ayuntamientos",
        "fetcher_code":       "File Download",
        "publisher_acronimo": "MINHAC-EL",
        "target_table":       "hacienda_deuda_viva_el",
        "schedule":           "0 5 1 7 *",   # yearly, 1 Jul 05:00 (Hacienda publica ~junio del año t+1)
        # Deuda viva consolidada de los ayuntamientos españoles publicada por Hacienda.
        # XLSX con una fila por municipio: cod_ine, nombre, importe deuda viva diciembre.
        # URL patrón: .../InformacionEELLs/{YYYY}/Deuda-viva-ayuntamientos-{YYYY}12.xlsx
        # El año se parametriza como is_external=True.
        "params": {
            "url":      {"value": "https://www.hacienda.gob.es/CDI/Sist%20Financiacion%20y%20Deuda/InformacionEELLs/2023/Deuda-viva-ayuntamientos-202312.xlsx", "is_external": True},
            "format":   "xlsx",
            "timeout":  "120",
            "headers":  '{"User-Agent": "Mozilla/5.0 (OpenDataManager/1.0)"}',
        },
    },
    # Cuenta General XBRL (rendiciondecuentas.es) eliminado:
    # el portal no expone API pública de descarga y requiere autenticación de la entidad.
    # El único KPI que necesita la Cuenta General y no es derivable de CONPREL es el
    # Remanente de Tesorería para Gastos Generales (RTGG). El resto de KPIs de
    # sostenibilidad (resultado presupuestario, ahorro bruto, ingresos/gastos corrientes)
    # se calculan directamente desde los datos CONPREL ya cargados en BD.
    {
        "name":               "Geonames - Entidades de Población (España)",
        "fetcher_code":       "Compressed File",
        "publisher_acronimo": None,
        "target_table":       "geo_elm",
        "schedule":           "0 3 1 1 *",   # yearly, 1 Jan 03:00
        # Geonames ES.zip → ES.txt (TSV, sin cabecera, columnas fijas)
        # Columnas: geonameid, name, asciiname, alternatenames, lat, lon,
        #           feature_class, feature_code, country, cc2,
        #           admin1, admin2, admin3 (código INE municipio 5 dígitos), admin4,
        #           population, elevation, dem, timezone, modification
        # Filtrar en SIPI-ETL: feature_class=P y feature_code in (PPL, PPLX, PPLL, PPLF, ...)
        "params": {
            "url":          "https://download.geonames.org/export/dump/ES.zip",
            "format":       "zip",
            "entry":        "ES.txt",
            "inner_format": "tsv",
            "timeout":      "120",
            "headers":      '{"User-Agent": "ODMGR/1.0 (investigacion patrimonial)"}',
            # ES.txt no tiene cabecera — definimos las columnas explícitamente
            "columns":      '["geonameid","name","asciiname","alternatenames","lat","lon","feature_class","feature_code","country","cc2","admin1","admin2","admin3","admin4","population","elevation","dem","timezone","modification"]',
        },
    },
]


# ---------------------------------------------------------------------------
# 4. APPLICATIONS (suscriptores que reciben webhooks al publicarse datasets)
# ---------------------------------------------------------------------------

APPLICATION_DEFS = [
    {
        "name":             "JerezBudgetAPI",
        "description":      (
            "API de análisis del rigor presupuestario del Ayuntamiento de Jerez de la Frontera. "
            "Consulta datos socioeconómicos vía GraphQL de ODM para el dashboard comparativo. "
            "Solo sincroniza localmente los datasets que necesita para JOINs SQL "
            "(padrón municipal para €/hab, cuenta general para KPIs de sostenibilidad)."
        ),
        "webhook_url":      "http://jerezbudget_api:8015/webhooks/odmgr",
        "webhook_secret":   {"value": "ODMGR_WEBHOOK_SECRET", "is_external": True},
        # "both": recibe ping HMAC → puede decidir si descarga o solo invalida caché;
        # para datos que solo necesita consultar usa /graphql/data de ODM directamente.
        "consumption_mode": "both",
        # Solo se suscribe para sincronización local a los dos recursos que necesita
        # en BD propia para JOINs con budget_lines (per-cápita, sostenibilidad).
        # El resto (renta, paro, EOH, PMP) se consultan en tiempo real vía GraphQL ODM.
        "subscribe_to": [
            "INE - Padrón Municipal (todos los municipios)",    # → ine_padron_municipal local
            "Hacienda - Deuda Viva de los Ayuntamientos",      # → cuenta_general_kpis (deuda_viva KPI)
            # "Cuenta General - Entidades Locales (XBRL)",     # pendiente: URL autenticada rendiciondecuentas.es
        ],
    },
]


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _retire_fetcher(db, code: str):
    """Soft-delete a legacy fetcher by code (leaves it in Trash, frees the code slot)."""
    from datetime import datetime, timezone
    ft = db.query(Fetcher).filter(Fetcher.code == code, Fetcher.deleted_at == None).first()
    if ft:
        ft.deleted_at = datetime.now(timezone.utc)
        db.flush()
        print(f"  ⚠ retired legacy fetcher '{code}'")


def _upsert_fetcher(db, defn: dict) -> Fetcher:
    """Create or update a Fetcher by code."""
    ft = db.query(Fetcher).filter(Fetcher.code == defn["code"]).first()
    if not ft:
        ft = Fetcher(id=uuid.uuid4(), code=defn["code"])
        db.add(ft)
    ft.class_path = defn["class_path"]
    ft.description = defn.get("description")
    ft.name = defn["code"]
    db.flush()

    # Sync param definitions (upsert: add missing, update description/group/default_value)
    existing: dict = {p.param_name: p for p in (ft.params_def or [])}
    for pd in defn.get("params", []):
        fp = existing.get(pd["param_name"])
        if fp is None:
            fp = FetcherParams(
                id=uuid.uuid4(),
                fetcher_id=ft.id,
                param_name=pd["param_name"],
                data_type=pd.get("data_type", "string"),
                required=pd.get("required", False),
                default_value=pd.get("default_value"),
                description=pd.get("description"),
                group=pd.get("group"),
            )
            db.add(fp)
        else:
            # Update mutable metadata fields
            fp.description = pd.get("description", fp.description)
            fp.group = pd.get("group", fp.group)
            fp.default_value = pd.get("default_value", fp.default_value)
    return ft


def _upsert_publisher(db, defn: dict) -> Publisher:
    """Create or update a Publisher by acronimo."""
    pub = db.query(Publisher).filter(Publisher.acronimo == defn["acronimo"]).first()
    if not pub:
        pub = Publisher(id=uuid.uuid4())
        db.add(pub)
    for k, v in defn.items():
        setattr(pub, k, v)
    db.flush()
    return pub


def _upsert_resource(db, defn: dict, fetchers: dict, publishers: dict) -> Resource:
    """Create or update a Resource by name."""
    ft = fetchers[defn["fetcher_code"]]
    pub = publishers.get(defn.get("publisher_acronimo"))

    res = db.query(Resource).filter(Resource.name == defn["name"]).first()
    if not res:
        res = Resource(id=uuid.uuid4(), name=defn["name"])
        db.add(res)

    res.fetcher_id = ft.id
    res.publisher_id = pub.id if pub else None
    res.publisher = pub.nombre if pub else None
    res.target_table = defn.get("target_table")
    res.schedule = defn.get("schedule")
    res.active = True
    db.flush()

    # Sync params: replace all (these are foundation resources, params are authoritative)
    # Each param value may be a plain string/number or a dict {"value": ..., "is_external": bool}
    existing = {p.key: p for p in (res.params or [])}
    seen = set()
    for key, spec in defn.get("params", {}).items():
        seen.add(key)
        if isinstance(spec, dict):
            raw_value = str(spec["value"])
            is_external = bool(spec.get("is_external", False))
        else:
            raw_value = str(spec)
            is_external = False
        if key in existing:
            existing[key].value = raw_value
            existing[key].is_external = is_external
        else:
            db.add(ResourceParam(id=uuid.uuid4(), resource_id=res.id, key=key,
                                 value=raw_value, is_external=is_external))

    # Remove params no longer in definition
    for key, param in existing.items():
        if key not in seen:
            db.delete(param)

    return res


def _upsert_application(db, defn: dict, resources_by_name: dict) -> Application:
    """Create or update an Application and its resource subscriptions."""
    app = db.query(Application).filter(Application.name == defn["name"]).first()
    if not app:
        app = Application(id=uuid.uuid4(), name=defn["name"])
        db.add(app)

    app.description = defn.get("description")
    app.webhook_url = defn.get("webhook_url")
    app.consumption_mode = defn.get("consumption_mode", "webhook")
    app.active = True

    secret_spec = defn.get("webhook_secret")
    if isinstance(secret_spec, dict):
        # is_external → use the env var name as placeholder (actual secret injected at runtime)
        app.webhook_secret = secret_spec.get("value", "")
    elif secret_spec:
        app.webhook_secret = secret_spec

    db.flush()

    # Subscriptions
    existing_subs = {s.resource_id: s for s in (app.subscriptions or [])}
    for resource_name in defn.get("subscribe_to", []):
        res = resources_by_name.get(resource_name)
        if not res:
            print(f"    ⚠ resource '{resource_name}' not found — skipping subscription")
            continue
        if res.id not in existing_subs:
            sub = DatasetSubscription(
                id=uuid.uuid4(),
                application_id=app.id,
                resource_id=res.id,
                auto_upgrade="patch",
            )
            db.add(sub)
            print(f"    + subscribed to '{resource_name}'")

    return app


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def seed():
    db = SessionLocal()
    try:
        print("[seed] Syncing fetchers...")
        # Retire legacy fetchers that were replaced
        _retire_fetcher(db, "Servicios Geográficos")

        fetchers = {}
        for defn in FETCHER_DEFS:
            ft = _upsert_fetcher(db, defn)
            fetchers[defn["code"]] = ft
            print(f"  ✓ {defn['code']}")

        print("[seed] Syncing publishers...")
        publishers = {}
        for defn in PUBLISHER_DEFS:
            pub = _upsert_publisher(db, defn)
            publishers[defn["acronimo"]] = pub
            print(f"  ✓ {defn['acronimo']} — {defn['nombre']}")

        print("[seed] Syncing foundation resources...")
        resources_by_name = {}
        for defn in RESOURCE_DEFS:
            res = _upsert_resource(db, defn, fetchers, publishers)
            resources_by_name[defn["name"]] = res
            print(f"  ✓ {defn['name']} → {defn['target_table']}")

        print("[seed] Syncing applications...")
        for defn in APPLICATION_DEFS:
            _upsert_application(db, defn, resources_by_name)
            print(f"  ✓ {defn['name']}")

        db.commit()
        print("[seed] Done.")
    except Exception as e:
        db.rollback()
        print(f"[seed] ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
