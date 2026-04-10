"""
Seeding inicial de OpenDataManager.
Idempotente: safe to run on every startup. Uses upsert-by-name semantics.

Orden:
  1. Fetchers   — sincroniza tipos de fetcher desde el código
  2. Publishers — organismos base del estado español
  3. Resources  — recursos fundacionales (referencia: DIR3, geografía)
"""
import uuid
from app.database import SessionLocal
from app.models import Fetcher, FetcherParams, Publisher, Resource, ResourceParam


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

    # Sync param definitions (add missing ones, don't delete existing)
    existing_params = {p.param_name for p in (ft.params_def or [])}
    for pd in defn.get("params", []):
        if pd["param_name"] not in existing_params:
            fp = FetcherParams(
                id=uuid.uuid4(),
                fetcher_id=ft.id,
                param_name=pd["param_name"],
                data_type=pd.get("data_type", "string"),
                required=pd.get("required", False),
                default_value=pd.get("default_value"),
            )
            db.add(fp)
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
        for defn in RESOURCE_DEFS:
            res = _upsert_resource(db, defn, fetchers, publishers)
            print(f"  ✓ {defn['name']} → {defn['target_table']}")

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
