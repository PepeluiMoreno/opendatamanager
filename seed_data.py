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
             "description": "Lista JSON de valores sobre los que pivotar."},
            {"param_name": "pivot_field",     "data_type": "string", "required": False, "group": "pivot_static",
             "default_value": "pivot_value",
             "description": "Nombre del campo que se añade a cada registro con el valor del pivot actual."},
            # ── Grupo: Pivot dinámico ODMGR ────────────────────────────────────────
            {"param_name": "pivot_source_odmgr_query",  "data_type": "string", "required": False, "group": "pivot_source"},
            {"param_name": "pivot_source_field",        "data_type": "string", "required": False, "group": "pivot_source"},
            {"param_name": "pivot_source_odmgr_url",    "data_type": "string", "required": False, "group": "pivot_source"},
            {"param_name": "pivot_source_filter_field", "data_type": "string", "required": False, "group": "pivot_source"},
            {"param_name": "pivot_source_filter_value", "data_type": "string", "required": False, "group": "pivot_source"},
            # ── Grupo: Extracción de registros ─────────────────────────────────────
            {"param_name": "record_selector",       "data_type": "string", "required": True,  "group": "extraction"},
            {"param_name": "field_attrs",           "data_type": "json",   "required": False, "group": "extraction"},
            {"param_name": "field_selectors",       "data_type": "json",   "required": False, "group": "extraction"},
            {"param_name": "field_attr_selectors",  "data_type": "json",   "required": False, "group": "extraction"},
            {"param_name": "field_all_text",        "data_type": "json",   "required": False, "group": "extraction"},
            {"param_name": "field_all_separator",   "data_type": "string", "required": False, "group": "extraction",
             "default_value": " | "},
            {"param_name": "required_field",        "data_type": "string", "required": False, "group": "extraction"},
            # ── Grupo: Paginación ───────────────────────────────────────────────────
            {"param_name": "next_page_selector",  "data_type": "string",  "required": False, "group": "pagination"},
            {"param_name": "next_page_attr",      "data_type": "string",  "required": False, "group": "pagination",
             "default_value": "href"},
            {"param_name": "max_pages",           "data_type": "integer", "required": False, "group": "pagination",
             "default_value": 500},
            {"param_name": "delay_between_pages", "data_type": "number",  "required": False, "group": "pagination",
             "default_value": 1.5},
            # ── Grupo: Comportamiento ───────────────────────────────────────────────
            {"param_name": "delay_between_pivots", "data_type": "number",  "required": False, "group": "behavior",
             "default_value": 2.0},
            {"param_name": "stop_on_error",        "data_type": "boolean", "required": False, "group": "behavior",
             "default_value": False},
            {"param_name": "headers",              "data_type": "json",    "required": False, "group": "behavior"},
            {"param_name": "timeout",              "data_type": "integer", "required": False, "group": "behavior",
             "default_value": 30},
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
            {"param_name": "url",             "data_type": "string",  "required": True,  "group": "http"},
            {"param_name": "method",          "data_type": "string",  "required": False, "default_value": "GET", "group": "http"},
            {"param_name": "query_params",    "data_type": "json",    "required": False, "group": "http"},
            {"param_name": "headers",         "data_type": "json",    "required": False, "group": "http"},
            {"param_name": "timeout",         "data_type": "integer", "required": False, "default_value": 120, "group": "http"},
            {"param_name": "root_path",       "data_type": "string",  "required": False, "group": "structure"},
            {"param_name": "meta_container",  "data_type": "string",  "required": False, "default_value": "MetaData", "group": "structure"},
            {"param_name": "meta_code_field", "data_type": "string",  "required": False, "default_value": "Codigo", "group": "structure"},
            {"param_name": "meta_name_field", "data_type": "string",  "required": False, "default_value": "Nombre", "group": "structure"},
            {"param_name": "meta_dim_path",   "data_type": "string",  "required": False, "default_value": "Variable.Codigo", "group": "structure"},
            {"param_name": "data_container",  "data_type": "string",  "required": False, "default_value": "Data", "group": "structure"},
            {"param_name": "period_field",    "data_type": "string",  "required": False, "default_value": "Anyo", "group": "structure"},
            {"param_name": "subperiod_field", "data_type": "string",  "required": False, "default_value": "Periodo", "group": "structure"},
            {"param_name": "value_field",     "data_type": "string",  "required": False, "default_value": "Valor", "group": "structure"},
            {"param_name": "secret_field",    "data_type": "string",  "required": False, "default_value": "Secreto", "group": "structure"},
            {"param_name": "serie_name_field","data_type": "string",  "required": False, "default_value": "Nombre", "group": "structure"},
            {"param_name": "flatten_mode",    "data_type": "string",  "required": False, "default_value": "long", "group": "output"},
            {"param_name": "batch_size",      "data_type": "integer", "required": False, "default_value": 500, "group": "output"},
        ],
    },
    {
        "code": "XBRL ZIP",
        "class_path": "app.fetchers.xbrl.XbrlFetcher",
        "description": (
            "Generic fetcher for ZIP archives containing XBRL documents. "
            "Extracts numeric elements with their period contexts into tabular records."
        ),
        "params": [
            {"param_name": "url",            "data_type": "string",  "required": True,  "group": "http"},
            {"param_name": "method",         "data_type": "string",  "required": False, "default_value": "GET", "group": "http"},
            {"param_name": "query_params",   "data_type": "json",    "required": False, "group": "http"},
            {"param_name": "headers",        "data_type": "json",    "required": False, "group": "http"},
            {"param_name": "timeout",        "data_type": "integer", "required": False, "default_value": 120, "group": "http"},
            {"param_name": "xml_pattern",    "data_type": "string",  "required": False, "group": "zip"},
            {"param_name": "entry",          "data_type": "string",  "required": False, "group": "zip"},
            {"param_name": "file_classifier","data_type": "json",    "required": False, "group": "zip"},
            {"param_name": "context_fields", "data_type": "json",    "required": False, "group": "output"},
            {"param_name": "account_prefix", "data_type": "string",  "required": False, "group": "output"},
            {"param_name": "exclude_tags",   "data_type": "string",  "required": False, "group": "output"},
            {"param_name": "batch_size",     "data_type": "integer", "required": False, "default_value": 200, "group": "output"},
        ],
    },
    {
        "code": "PDF_TABLE",
        "class_path": "app.fetchers.pdf_table.PdfTableFetcher",
        "description": (
            "Fetcher for PDFs: iterates a year/month/quarter date range, builds a URL "
            "per period from url_template, downloads each PDF and extracts tables with pdfplumber."
        ),
        "params": [
            {"param_name": "url_template", "data_type": "string",  "required": True,
             "group": "url",
             "description": "URL template. Use {year}, {month} (zero-padded), {quarter} as placeholders."},
            {"param_name": "granularity",  "data_type": "string",  "required": True,
             "group": "date_range",
             "description": "Iteration granularity: 'annual', 'quarterly' or 'monthly'."},
            {"param_name": "year_from",    "data_type": "integer", "required": True,  "group": "date_range"},
            {"param_name": "year_to",      "data_type": "integer", "required": True,  "group": "date_range"},
            {"param_name": "table_index",  "data_type": "integer", "required": False, "default_value": 0,
             "group": "extraction",
             "description": "0-based index of the table to extract from each PDF page."},
            {"param_name": "header_row",   "data_type": "integer", "required": False, "default_value": 0,
             "group": "extraction",
             "description": "Row index to use as column headers."},
            {"param_name": "timeout",      "data_type": "integer", "required": False, "default_value": 60,
             "group": "http"},
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
    {
        "acronimo": "AJFRA",
        "nombre":   "Ayuntamiento de Jerez de la Frontera",
        "nivel":    "LOCAL",
        "pais":     "España",
        "comunidad_autonoma": "Andalucía",
        "provincia": "Cádiz",
        "municipio": "Jerez de la Frontera",
        "portal_url": "https://transparencia.jerez.es",
    },
]


# ---------------------------------------------------------------------------
# 3. FOUNDATION RESOURCES
# ---------------------------------------------------------------------------

_BASE_JEREZ = "https://transparencia.jerez.es/infopublica/economica"

RESOURCE_DEFS = [
    {
        "name":             "DIR3 - Unidades Orgánicas de España",
        "fetcher_code":     "API REST",
        "publisher_acronimo": "JDA",
        "target_table":     "dir3_unidades",
        "schedule":         "0 3 * * 0",
        "params": {
            "url":     "https://datos.juntadeandalucia.es/api/v0/dir3/all?format=json",
            "method":  "GET",
            "timeout": "120",
            "id_field": "id",
        },
    },
    {
        "name":             "España - Municipios (INE)",
        "fetcher_code":     "File Download",
        "publisher_acronimo": "INE",
        "target_table":     "geo_municipios",
        "schedule":         "0 4 1 1 *",
        "params": {
            "url":       "https://www.ine.es/daco/daco42/codmun/26codmun.xlsx",
            "format":    "xlsx",
            "skip_rows": "2",
            "timeout":   "60",
            "headers":   '{"User-Agent": "Mozilla/5.0", "Referer": "https://www.ine.es/"}',
        },
    },
    {
        "name":             "España - Provincias (INE)",
        "fetcher_code":     "API REST",
        "publisher_acronimo": "INE",
        "target_table":     "geo_provincias",
        "schedule":         "0 4 1 1 *",
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
        "schedule":         "0 4 1 1 *",
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
        "schedule":         "0 4 * * 0",
        "params": {
            "url":            "https://proveedores.face.gob.es/api/v1/relations",
            "method":         "GET",
            "timeout":        "60",
            "page_param":     "page",
            "page_size_param": "limit",
            "page_size":      "1000",
            "content_field":  "items",
            "id_field":       "",
            "headers":        '{"User-Agent": "Python/requests", "Accept": "application/json"}',
            "page_start":     "1",
        },
    },
    {
        "name":             "Notarías - Guía Notarial (CGN)",
        "fetcher_code":     "REST Loop",
        "publisher_acronimo": "CGN",
        "target_table":     "notarios",
        "schedule":         "0 2 * * 0",
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
            "endpoint":     "http://ovc.catastro.meh.es/INSPIRE/wfsCP.aspx",
            "typenames":    "cp:CadastralParcel",
            "bbox":         "-6.4,36.9,-5.3,37.9",
            "outputFormat": "application/gml+xml; version=3.2",
            "srsName":      "EPSG:4326",
            "count":        "500",
            "id_field":     "nationalCadastralReference",
            "timeout":      "120",
        },
    },
    {
        "name":               "OSM - Inmuebles Eclesiásticos (España)",
        "fetcher_code":       "OSM Overpass",
        "publisher_acronimo": None,
        "target_table":       "osm_inmuebles_eclesiasticos",
        "schedule":           "0 2 * * 0",
        "params": {
            "use_types":     '[{"preset": "RELIGIOUS_ALL"}, {"preset": "RELIGIOUS_BUILDING_EXTRA"}]',
            "demarcacion":   "España",
            "element_types": "node,way,relation",
            "out_format":    "center",
            "timeout":       "1800",
            "max_elements":  "0",
        },
    },
    {
        "name":               "BDNS - Concesiones de Subvenciones",
        "fetcher_code":       "API REST Paginada",
        "publisher_acronimo": "BDNS",
        "target_table":       "bdns_concesiones",
        "schedule":           "0 4 * * 1",
        "params": {
            "url":            "https://www.infosubvenciones.es/bdnstrans/api/concesiones/busqueda",
            "page_param":     "page",
            "page_size_param": "pageSize",
            "page_size":      "10000",
            "content_field":  "content",
            "id_field":       "id",
            "fechaDesde":     {"value": "01/01/2026", "is_external": True},
            "fechaHasta":     {"value": "31/12/2026", "is_external": True},
        },
    },
    {
        "name":               "BDNS - Convocatorias de Subvenciones",
        "fetcher_code":       "API REST Paginada",
        "publisher_acronimo": "BDNS",
        "target_table":       "bdns_grants",
        "schedule":           "0 3 * * 1",
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
            "fechaDesde":     {"value": "01/01/2026", "is_external": True},
            "fechaHasta":     {"value": "31/12/2026", "is_external": True},
        },
    },
    {
        "name":               "Registros de la Propiedad (CORPME)",
        "fetcher_code":       "File Download",
        "publisher_acronimo": "CORPME",
        "target_table":       "registros_propiedad",
        "schedule":           "0 3 1 * *",
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
        "schedule":           "0 2 1 * *",
        "params": {
            "url_template":   "https://www.fotocasa.es/buscar-agencias-inmobiliarias/{value}/todas-las-zonas/l",
            "pivot_values":   (
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
            "record_selector":      "article[data-agency-id]",
            "field_attrs":          '{"agency_id": "data-agency-id", "nombre": "data-agency-name"}',
            "field_attr_selectors": '{"url_busqueda": {"selector": "button[data-promiseref]", "attr": "data-promiseref"}}',
            "field_all_text":       '{"estadisticas": ".re-description-item label"}',
            "next_page_selector":   'a[rel="next"]',
            "pivot_field":          "provincia",
            "delay_between_pages":  "1.5",
            "delay_between_pivots": "2.0",
            "max_pages":            "500",
            "timeout":              "30",
        },
    },
    {
        "name":               "Agencias Inmobiliarias (RERA Andalucía)",
        "fetcher_code":       "API REST Paginada",
        "publisher_acronimo": "JDA",
        "target_table":       "agencias_inmobiliarias",
        "schedule":           "0 4 * * 0",
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
        "schedule":           "0 3 1 1 *",
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
        "schedule":           "0 3 * * 1",
        "params": {
            "url_template":             "{value}",
            "page_base_url":            "https://www.fotocasa.es",
            "pivot_source_odmgr_query": "agenciasInmobiliariasFotocasa",
            "pivot_source_field":       "url_busqueda",
            "pivot_values":   (
                '["https://www.fotocasa.es/es/inmobiliaria-ikesa/comprar/inmuebles/sevilla-provincia/todas-las-zonas/l?clientId=9202760540246",'
                ' "https://www.fotocasa.es/es/inmobiliaria-winning-properties/comprar/inmuebles/sevilla-provincia/todas-las-zonas/l?clientId=9202751942277"]'
            ),
            "pivot_field":          "agencia_provincia_url",
            "record_selector":      "article",
            "field_attr_selectors": (
                '{"url_path":       {"selector": "h3 a", "attr": "href"},'
                ' "agencia_url":    {"selector": "a[data-panot-component=\'link-box-raised\']", "attr": "href"},'
                ' "agencia_nombre": {"selector": "a[data-panot-component=\'link-box-raised\'] img", "attr": "alt"}}'
            ),
            "field_selectors":      (
                '{"precio":    "[class*=\'text-display-3\'] span",'
                ' "titulo":    "h3",'
                ' "municipio": "p[class*=\'opacity-75\']"}'
            ),
            "field_all_text":       '{"caracteristicas": "ul[class*=\'text-body-1\'] li"}',
            "next_page_selector":   'a[aria-label="Página siguiente"]',
            "required_field":       "url_path",
            "delay_between_pages":  "2.0",
            "delay_between_pivots": "5.0",
            "max_pages":            "500",
            "timeout":              "30",
        },
    },
    {
        "name":               "INE - Padrón Municipal (todos los municipios)",
        "fetcher_code":       "JSON Time Series",
        "publisher_acronimo": "INE",
        "target_table":       "ine_padron_municipal",
        "schedule":           "0 5 15 6 *",
        "params": {
            "url":             "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/2852",
            "query_params":    '{"nult": "10", "det": "2"}',
            "headers":         '{"User-Agent": "Mozilla/5.0 (OpenDataManager/1.0; +https://github.com/PepeluiMoreno)"}',
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
            "batch_size":      "1000",
        },
    },
    {
        "name":               "INE - Atlas de Distribución de Renta (municipios)",
        "fetcher_code":       "JSON Time Series",
        "publisher_acronimo": "INE",
        "target_table":       "ine_renta_municipal",
        "schedule":           "0 5 1 11 *",
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
        "schedule":           "0 6 25 * *",
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
        "schedule":           "0 7 10 1 *",
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
        "schedule":           "0 7 20 * *",
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
        "schedule":           "0 5 1 7 *",
        "params": {
            "url":     {"value": "https://www.hacienda.gob.es/CDI/Sist%20Financiacion%20y%20Deuda/InformacionEELLs/2023/Deuda-viva-ayuntamientos-202312.xlsx", "is_external": True},
            "format":  "xlsx",
            "timeout": "120",
            "headers": '{"User-Agent": "Mozilla/5.0 (OpenDataManager/1.0)"}',
        },
    },
    {
        "name":               "Geonames - Entidades de Población (España)",
        "fetcher_code":       "Compressed File",
        "publisher_acronimo": None,
        "target_table":       "geo_elm",
        "schedule":           "0 3 1 1 *",
        "params": {
            "url":          "https://download.geonames.org/export/dump/ES.zip",
            "format":       "zip",
            "entry":        "ES.txt",
            "inner_format": "tsv",
            "timeout":      "120",
            "headers":      '{"User-Agent": "ODMGR/1.0 (investigacion patrimonial)"}',
            "columns":      '["geonameid","name","asciiname","alternatenames","lat","lon","feature_class","feature_code","country","cc2","admin1","admin2","admin3","admin4","population","elevation","dem","timezone","modification"]',
        },
    },
    # ── Recursos Jerez de la Frontera (transparencia.jerez.es) ────────────────
    {
        "name":               "Jerez - PMP Mensual (Ley 15/2010)",
        "fetcher_code":       "PDF_TABLE",
        "publisher_acronimo": "AJFRA",
        "target_table":       "jerez_pmp_mensual",
        "schedule":           "0 3 10 * *",   # mensual, día 10 a las 03:00
        "params": {
            "url_template": f"{_BASE_JEREZ}/c-deuda/{{year}}/pmp/Informe_PMP_{{year}}_{{month}}.pdf",
            "granularity":  "monthly",
            "year_from":    "2020",
            "year_to":      {"value": "2025", "is_external": True},
            "table_index":  "0",
            "header_row":   "0",
        },
    },
    {
        "name":               "Jerez - Morosidad Trimestral (Ley 15/2010)",
        "fetcher_code":       "PDF_TABLE",
        "publisher_acronimo": "AJFRA",
        "target_table":       "jerez_morosidad_trimestral",
        "schedule":           "0 3 15 1,4,7,10 *",   # trimestral
        "params": {
            "url_template": f"{_BASE_JEREZ}/c-deuda/{{year}}/morosidad/Informe_Ta_Ley_15_10-{{year}}-{{quarter}}oT.pdf",
            "granularity":  "quarterly",
            "year_from":    "2020",
            "year_to":      {"value": "2025", "is_external": True},
            "table_index":  "0",
            "header_row":   "0",
        },
    },
    {
        "name":               "Jerez - Deuda Financiera Anual",
        "fetcher_code":       "PDF_TABLE",
        "publisher_acronimo": "AJFRA",
        "target_table":       "jerez_deuda_financiera",
        "schedule":           "0 3 1 7 *",   # anual, 1 julio
        "params": {
            "url_template": f"{_BASE_JEREZ}/c-deuda/{{year}}/deuda/DEUDA_FINANCIERA_31-12-{{year}}.pdf",
            "granularity":  "annual",
            "year_from":    "2020",
            "year_to":      {"value": "2024", "is_external": True},
            "table_index":  "0",
            "header_row":   "0",
        },
    },
    {
        "name":               "Jerez - Coste Efectivo de Servicios (CESEL)",
        "fetcher_code":       "PDF_TABLE",
        "publisher_acronimo": "AJFRA",
        "target_table":       "jerez_cesel",
        "schedule":           "0 3 1 7 *",   # anual, 1 julio
        # CESEL es XLSX en producción — sustituir fetcher_code por File Download
        # cuando se implemente S14. Por ahora usa PDF_TABLE como placeholder.
        "params": {
            "url_template": f"{_BASE_JEREZ}/e-otrainfo/costeservicios/CESEL-{{year}}.xlsx",
            "granularity":  "annual",
            "year_from":    "2015",
            "year_to":      {"value": "2021", "is_external": True},
        },
    },
]


# ---------------------------------------------------------------------------
# 4. APPLICATIONS
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
        "consumption_mode": "both",
        "subscribe_to": [
            "INE - Padrón Municipal (todos los municipios)",
            "Hacienda - Deuda Viva de los Ayuntamientos",
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
        app.webhook_secret = secret_spec.get("value", "")
    elif secret_spec:
        app.webhook_secret = secret_spec

    db.flush()

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
