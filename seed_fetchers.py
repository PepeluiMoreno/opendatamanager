"""
Alta inicial de fetchers usando la API de administración GraphQL.

Este script es la única carga automática de datos iniciales que debe ejecutarse
en despliegue. Todo lo demás (resources, publishers, aplicaciones, datos de
casos de uso) debe tratarse fuera del bootstrap base.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, List

from app.graphql.schema import schema


FETCHERS: List[Dict[str, Any]] = [
    {
        "name": "API REST",
        "class_path": "app.fetchers.rest.RestFetcher",
        "description": "Especie REST genérica (HTTP+JSON). El recorrido del conjunto se delega en la categoría 'paginación': sin 'pagination' (o 'none') hace una sola petición; con una estrategia (query_offset, page_number, rel_next, cursor, pivot_loop) recorre y acumula los registros de 'content_field'. Unifica la familia REST (absorbe 'API REST Paginada').",
        "params": [
            {"param_name": "url", "data_type": "string", "required": True, "group": "http"},
            {"param_name": "method", "data_type": "string", "required": False, "default_value": "GET", "group": "http"},
            {"param_name": "headers", "data_type": "json", "required": False, "group": "http"},
            {"param_name": "query_params", "data_type": "json", "required": False, "group": "http"},
            {"param_name": "timeout", "data_type": "integer", "required": False, "default_value": 30, "group": "http"},
            {"param_name": "max_retries", "data_type": "integer", "required": False, "default_value": 3, "group": "http"},
            {"param_name": "pagination", "data_type": "string", "required": False, "default_value": "none", "group": "paginacion",
             "hint": "none | query_offset | page_number | rel_next | cursor | pivot_loop"},
            {"param_name": "content_field", "data_type": "string", "required": False, "group": "extraccion",
             "hint": "Ruta (con puntos) a la lista de registros en cada página, p. ej. 'content' o 'data.items'."},
            {"param_name": "extraction", "data_type": "string", "required": False, "default_value": "passthrough", "group": "extraccion",
             "hint": "passthrough | field_map | timeseries_long | bindings. Aplana la respuesta a registros planos."},
            {"param_name": "field_map", "data_type": "json", "required": False, "group": "extraccion",
             "hint": "Para extraction=field_map: {campo_salida: ruta.con.puntos}."},
            {"param_name": "page_size", "data_type": "integer", "required": False, "group": "paginacion"},
            {"param_name": "next_link_field", "data_type": "string", "required": False, "group": "paginacion",
             "hint": "Para pagination=rel_next sobre JSON: ruta al enlace de la siguiente página."},
            {"param_name": "cursor_field", "data_type": "string", "required": False, "group": "paginacion",
             "hint": "Para pagination=cursor: ruta al token de la siguiente página en la respuesta."},
            {"param_name": "request", "data_type": "string", "required": False, "default_value": "query", "group": "peticion",
             "hint": "query | json_body | form | graphql | sparql. Cómo se construye el cuerpo de la petición."},
            {"param_name": "payload_template", "data_type": "json", "required": False, "group": "peticion",
             "hint": "Para request=json_body/form: plantilla de cuerpo; usa {pivot} para el valor iterado (pagination=pivot_loop)."},
            {"param_name": "pivot_param", "data_type": "string", "required": False, "group": "paginacion",
             "hint": "Para pagination=pivot_loop: nombre del parámetro/marcador del valor iterado."},
            {"param_name": "pivot_values", "data_type": "json", "required": False, "group": "paginacion",
             "hint": "Para pagination=pivot_loop: lista de valores a iterar (una petición por valor)."},
            {"param_name": "graphql_query", "data_type": "string", "required": False, "group": "peticion"},
            {"param_name": "sparql_query", "data_type": "string", "required": False, "group": "peticion"},
        ],
    },
    {
        "name": "Feeds ATOM/RSS",
        "class_path": "app.fetchers.atom.AtomFetcher",
        "description": "ATOM/RSS feed reader",
        "params": [
            {"param_name": "url", "data_type": "string", "required": True, "group": "http"},
            {"param_name": "max_items", "data_type": "integer", "required": False, "default_value": 1000, "group": "behavior"},
            {"param_name": "pagination", "data_type": "string", "required": False, "default_value": "query", "group": "comportamiento",
             "hint": "query (offset por params) o rel_next (sigue link rel=next; sindicaciones tipo PLACSP)."},
            {"param_name": "field_map", "data_type": "json", "required": False, "group": "extraccion",
             "hint": "Mapa {campo_salida: ruta_local} para aplanar cada entry (p. ej. CODICE).",
             "help_md": "Rutas por nombre de etiqueta, anidables con '/'. Atributos con 'tag@attr'. Sin field_map, cada entry se devuelve como dict anidado."},
            {"param_name": "delay", "data_type": "integer", "required": False, "default_value": 0, "group": "comportamiento",
             "hint": "Segundos de cortesía entre páginas."},
            {"param_name": "desde", "data_type": "string", "required": False, "group": "incremental",
             "hint": "Suelo temporal: fecha ISO (solo entradas desde esa fecha) o 'auto' (incremental: desde la última ejecución completada).",
             "help_md": "Para feeds en orden descendente, la paginación se detiene al alcanzar entradas anteriores. 'auto' usa la marca de agua de la ejecución previa, evitando depender de max_pages."},
            {"param_name": "date_field", "data_type": "string", "required": False, "default_value": "fecha", "group": "incremental",
             "hint": "Campo de salida que contiene la fecha de la entrada (por defecto 'fecha')."}
        ],
    },
    {
        "name": "PLACSP CODICE (ATOM)",
        "class_path": "app.fetchers.atom.AtomFetcher",
        "description": "VARIANTE de 'Feeds ATOM/RSS' para sindicaciones CODICE 2.07 (PLACSP, agregadas, menores, encargos, consultas, Comunidad de Madrid). Las peculiaridades CODICE (paginación rel_next, field_map, incremental) viven en preset_params; el recurso solo aporta la 'url'.",
        "params": [
            {"param_name": "url", "data_type": "string", "required": True, "group": "http",
             "hint": "URL del índice ATOM de la sindicación CODICE."},
        ],
        "preset_params": {"pagination": "rel_next", "date_field": "fecha", "delay": 2, "timeout": 180, "max_pages": 6, "desde": "auto", "field_map": {"expediente": "ContractFolderID", "estado": "ContractFolderStatusCode", "titulo": "title", "objeto": "ProcurementProject/Name", "tipo_codigo": "ProcurementProject/TypeCode", "subtipo_codigo": "ProcurementProject/SubTypeCode", "cpv": "ItemClassificationCode", "importe": "TotalAmount", "valor_estimado": "EstimatedOverallContractAmount", "organo_contratacion": "LocatedContractingParty/PartyName/Name", "provincia": "CountrySubentity", "provincia_codigo": "CountrySubentityCode", "adjudicatario": "WinningParty/PartyName/Name", "fecha": "updated", "url": "link@href"}},
    },
    {
        "name": "File Download",
        "class_path": "app.fetchers.file_download.FileDownloadFetcher",
        "description": "Downloads a static file and converts rows to records. Supports PDF, XLS, XLSX, CSV and TSV.",
        "params": [
            {"param_name": "url", "data_type": "string", "required": True, "group": "http"},
            {"param_name": "format", "data_type": "string", "required": True, "group": "format"},
            {"param_name": "sheet", "data_type": "string", "required": False, "default_value": "0", "group": "excel"},
            {"param_name": "skip_rows", "data_type": "integer", "required": False, "default_value": 0, "group": "tabular"},
            {"param_name": "delimiter", "data_type": "string", "required": False, "group": "tabular"},
            {"param_name": "encoding", "data_type": "string", "required": False, "default_value": "utf-8-sig", "group": "tabular"},
            {"param_name": "columns", "data_type": "json", "required": False, "group": "tabular"},
            {"param_name": "headers", "data_type": "json", "required": False, "group": "http"},
            {"param_name": "batch_size", "data_type": "integer", "required": False, "default_value": 1000, "group": "behavior"},
            {"param_name": "timeout", "data_type": "integer", "required": False, "default_value": 60, "group": "http"},
            {"param_name": "table_index", "data_type": "integer", "required": False, "default_value": 0, "group": "pdf"},
            {"param_name": "header_row", "data_type": "integer", "required": False, "default_value": 0, "group": "pdf"},
            {"param_name": "custom_parser", "data_type": "string", "required": False, "group": "specialization"},
        ],
    },
    {
        "name": "Compressed File",
        "class_path": "app.fetchers.compressed_file.CompressedFileFetcher",
        "description": "Downloads a compressed archive and parses the extracted file as PDF, XLS, XLSX, CSV or TSV.",
        "params": [
            {"param_name": "url", "data_type": "string", "required": True, "group": "http"},
            {"param_name": "format", "data_type": "string", "required": True, "group": "archive"},
            {"param_name": "entry", "data_type": "string", "required": False, "group": "archive"},
            {"param_name": "inner_format", "data_type": "string", "required": False, "group": "format"},
            {"param_name": "skip_rows", "data_type": "integer", "required": False, "default_value": 0, "group": "tabular"},
            {"param_name": "delimiter", "data_type": "string", "required": False, "group": "tabular"},
            {"param_name": "encoding", "data_type": "string", "required": False, "default_value": "utf-8-sig", "group": "tabular"},
            {"param_name": "sheet", "data_type": "string", "required": False, "default_value": "0", "group": "excel"},
            {"param_name": "columns", "data_type": "json", "required": False, "group": "tabular"},
            {"param_name": "headers", "data_type": "json", "required": False, "group": "http"},
            {"param_name": "batch_size", "data_type": "integer", "required": False, "default_value": 1000, "group": "behavior"},
            {"param_name": "timeout", "data_type": "integer", "required": False, "default_value": 120, "group": "http"},
            {"param_name": "table_index", "data_type": "integer", "required": False, "default_value": 0, "group": "pdf"},
            {"param_name": "header_row", "data_type": "integer", "required": False, "default_value": 0, "group": "pdf"},
            {"param_name": "custom_parser", "data_type": "string", "required": False, "group": "specialization"},
        ],
    },
    {
        "name": "HTML SearchLoop",
        "class_path": "app.fetchers.searchloop_html.SearchLoopHtmlFetcher",
        "description": "HTML scraper that pivots over <select> option values",
        "params": [
            # ── Descubrimiento ──────────────────────────────────────────
            {"param_name": "url", "data_type": "string", "required": True, "group": "descubrimiento",
             "hint": "URL de la página con el formulario de búsqueda",
             "help_md": "Página HTML que contiene el `<select>` sobre cuyas opciones se itera. Se descarga primero para abrir sesión y descubrir los valores."},
            {"param_name": "search_field_name", "data_type": "string", "required": False, "group": "descubrimiento",
             "hint": "name/id del <select> a pivotar",
             "help_md": "Nombre (`name`) o `id` del desplegable cuyas opciones se recorren una a una. Ej.: `filtro.codigosComunidad`."},
            {"param_name": "search_field_values", "data_type": "string", "required": False, "group": "descubrimiento",
             "hint": "valores fijos separados por coma (opcional)",
             "help_md": "Si se indica, **no** se autodescubren las opciones del select: se usan estos valores (separados por coma)."},

            # ── Envío de la búsqueda ────────────────────────────────────
            {"param_name": "search_mode", "data_type": "string", "required": False, "default_value": "GET_simple", "group": "envio_busqueda",
             "hint": "Cómo se envía la búsqueda",
             "help_md": "Preset que fija método, codificación y convenciones del envío. Elige según cómo funcione el buscador del portal.",
             "enum_values": [
                 {"value": "GET_simple", "label": "GET simple", "help": "El buscador devuelve resultados por querystring (GET)."},
                 {"value": "POST_formulario", "label": "POST formulario", "help": "Envío POST urlencoded de un formulario clásico."},
                 {"value": "POST_struts", "label": "POST Struts2", "help": "Portales Struts2: POST multipart con sesión, arrastre de inputs hidden y campo compañero `__multiselect_`. Aviso: si el portal renderiza los resultados con JavaScript (struts2-jquery), no es accesible por HTTP puro."},
             ]},
            {"param_name": "search_action_url", "data_type": "string", "required": False, "group": "envio_busqueda",
             "hint": "URL de la acción de búsqueda (si difiere de url)",
             "help_md": "Endpoint al que se envía la búsqueda cuando es distinto de la página del formulario. Si se deja vacío, se intenta descubrir del atributo `action` del `<form>`.",
             "visible_when": {"param": "search_mode", "in": ["POST_formulario", "POST_struts"]}},
            {"param_name": "enctype", "data_type": "string", "required": False, "group": "envio_busqueda",
             "hint": "Codificación del POST",
             "help_md": "`urlencoded` (por defecto) o `multipart` (form-data). Struts2 suele requerir multipart.",
             "enum_values": [
                 {"value": "urlencoded", "label": "urlencoded", "help": "application/x-www-form-urlencoded."},
                 {"value": "multipart", "label": "multipart", "help": "multipart/form-data."},
             ],
             "visible_when": {"param": "search_mode", "in": ["POST_formulario", "POST_struts"]}},
            {"param_name": "multiselect_companion", "data_type": "boolean", "required": False, "group": "envio_busqueda",
             "hint": "Añadir campo compañero __multiselect_ (Struts2)",
             "help_md": "Convención de Struts2: por cada multiselect enviado se añade `__multiselect_<campo>=` vacío.",
             "visible_when": {"param": "search_mode", "in": ["POST_struts"]}},
            {"param_name": "carry_hidden_fields", "data_type": "boolean", "required": False, "group": "envio_busqueda",
             "hint": "Reenviar los <input hidden> del formulario",
             "help_md": "Parsea la página del formulario y reenvía todos sus inputs ocultos (tokens/estado). Necesario en muchos portales con estado.",
             "visible_when": {"param": "search_mode", "in": ["POST_formulario", "POST_struts"]}},
            {"param_name": "extra_params", "data_type": "json", "required": False, "group": "envio_busqueda",
             "hint": "Campos fijos adicionales {clave: valor}",
             "help_md": "Campos obligatorios o fijos que el formulario exige, como objeto JSON."},

            # ── Extracción de resultados ────────────────────────────────
            {"param_name": "rows_selector", "data_type": "string", "required": False, "default_value": "table tr", "group": "extraccion",
             "hint": "Selector CSS de las filas de resultados",
             "help_md": "Selector CSS que localiza cada fila de la tabla de resultados. Por defecto `table tr`."},
            {"param_name": "has_header", "data_type": "boolean", "required": False, "default_value": True, "group": "extraccion",
             "hint": "La primera fila es cabecera",
             "help_md": "Marca si la primera fila contiene los nombres de columna."},
            {"param_name": "levels", "data_type": "json", "required": False, "group": "extraccion",
             "hint": "Scraping recursivo por niveles (modo avanzado)",
             "help_md": "Alternativa al modo formulario: lista de niveles con selectores de campos y enlaces a subpáginas para scraping jerárquico."},

            # ── Paginación ──────────────────────────────────────────────
            {"param_name": "next_page_selector", "data_type": "string", "required": False, "group": "paginacion",
             "hint": "Selector CSS del enlace 'siguiente'",
             "help_md": "Selector del enlace de paginación; si está vacío, se asume una sola página."},
            {"param_name": "max_pages", "data_type": "integer", "required": False, "default_value": 50, "group": "paginacion",
             "hint": "Máximo de páginas por búsqueda",
             "help_md": "Tope de seguridad de páginas a recorrer por cada valor del select."},
            {"param_name": "delay_between_pages", "data_type": "number", "required": False, "default_value": 0.5, "group": "paginacion",
             "hint": "Pausa entre páginas (s)",
             "help_md": "Cortesía: segundos de espera entre peticiones de paginación."},
        ],
    },
    {
        "name": "HTML Paginated",
        "class_path": "app.fetchers.paginated_html.PaginatedHtmlFetcher",
        "description": "HTML scraper with automatic pagination",
        "params": [
            {"param_name": "url", "data_type": "string", "required": True, "group": "navigation"},
            {"param_name": "row_selector", "data_type": "string", "required": True, "group": "extraction"},
            {"param_name": "next_selector", "data_type": "string", "required": False, "group": "pagination"},
        ],
    },
    {
        "name": "HTML Forms",
        "class_path": "app.fetchers.html.HtmlFetcher",
        "description": "Simple HTML form GET/POST scraper",
        "params": [
            {"param_name": "url", "data_type": "string", "required": True, "group": "navigation"},
            {"param_name": "method", "data_type": "string", "required": False, "default_value": "GET", "group": "http"},
        ],
    },
    {
        "name": "OSM Overpass",
        "class_path": "app.fetchers.osm.OSMFetcher",
        "description": "OpenStreetMap Overpass API query",
        "params": [
            {"param_name": "query", "data_type": "overpass_query", "required": True, "group": "query"},
            {"param_name": "timeout", "data_type": "integer", "required": False, "default_value": 120, "group": "http"},
        ],
    },
    {
        "name": "WFS",
        "class_path": "app.fetchers.wfs.WFSFetcher",
        "description": "OGC Web Feature Service — vector features with automatic pagination",
        "params": [
            {"param_name": "endpoint", "data_type": "string", "required": True, "group": "request"},
            {"param_name": "typenames", "data_type": "string", "required": True, "group": "request"},
            {"param_name": "version", "data_type": "string", "required": False, "default_value": "2.0.0", "group": "request"},
            {"param_name": "outputFormat", "data_type": "string", "required": False, "default_value": "application/json", "group": "request"},
            {"param_name": "srsName", "data_type": "string", "required": False, "default_value": "EPSG:4326", "group": "request"},
            {"param_name": "bbox", "data_type": "bbox", "required": False, "group": "filter"},
            {"param_name": "cql_filter", "data_type": "string", "required": False, "group": "filter"},
            {"param_name": "count", "data_type": "integer", "required": False, "default_value": 1000, "group": "pagination"},
            {"param_name": "id_field", "data_type": "string", "required": False, "group": "behavior"},
            {"param_name": "timeout", "data_type": "integer", "required": False, "default_value": 120, "group": "http"},
        ],
    },
    {
        "name": "WMS",
        "class_path": "app.fetchers.wms.WMSFetcher",
        "description": "OGC Web Map Service — map image metadata + URL",
        "params": [
            {"param_name": "endpoint", "data_type": "string", "required": True, "group": "request"},
            {"param_name": "layers", "data_type": "string", "required": True, "group": "request"},
            {"param_name": "bbox", "data_type": "bbox", "required": True, "group": "request"},
            {"param_name": "version", "data_type": "string", "required": False, "default_value": "1.3.0", "group": "request"},
            {"param_name": "format", "data_type": "string", "required": False, "default_value": "image/png", "group": "request"},
            {"param_name": "crs", "data_type": "string", "required": False, "default_value": "EPSG:4326", "group": "request"},
            {"param_name": "styles", "data_type": "string", "required": False, "group": "request"},
            {"param_name": "width", "data_type": "integer", "required": False, "default_value": 1024, "group": "request"},
            {"param_name": "height", "data_type": "integer", "required": False, "default_value": 1024, "group": "request"},
            {"param_name": "timeout", "data_type": "integer", "required": False, "default_value": 120, "group": "http"},
        ],
    },
    {
        "name": "Servicios SOAP/WSDL",
        "class_path": "app.fetchers.soap.SoapFetcher",
        "description": "SOAP/WSDL web service",
        "params": [
            {"param_name": "wsdl", "data_type": "string", "required": True, "group": "request"},
            {"param_name": "operation", "data_type": "string", "required": True, "group": "request"},
        ],
    },
    {
        "name": "URL Loop HTML",
        "class_path": "app.fetchers.url_loop_html.UrlLoopHtmlFetcher",
        "description": "HTML scraper genérico con pivot, múltiples registros por página y paginación.",
        "params": [
            {"param_name": "url_template", "data_type": "string", "required": True, "group": "url"},
            {"param_name": "page_base_url", "data_type": "string", "required": False, "group": "url"},
            {"param_name": "pivot_values", "data_type": "json", "required": False, "group": "pivot_static"},
            {"param_name": "pivot_field", "data_type": "string", "required": False, "default_value": "pivot_value", "group": "pivot_static"},
            {"param_name": "pivot_source_odmgr_query", "data_type": "string", "required": False, "group": "pivot_source"},
            {"param_name": "pivot_source_field", "data_type": "string", "required": False, "group": "pivot_source"},
            {"param_name": "pivot_source_odmgr_url", "data_type": "string", "required": False, "group": "pivot_source"},
            {"param_name": "pivot_source_filter_field", "data_type": "string", "required": False, "group": "pivot_source"},
            {"param_name": "pivot_source_filter_value", "data_type": "string", "required": False, "group": "pivot_source"},
            {"param_name": "record_selector", "data_type": "string", "required": True, "group": "extraction"},
            {"param_name": "field_attrs", "data_type": "json", "required": False, "group": "extraction"},
            {"param_name": "field_selectors", "data_type": "json", "required": False, "group": "extraction"},
            {"param_name": "field_attr_selectors", "data_type": "json", "required": False, "group": "extraction"},
            {"param_name": "field_all_text", "data_type": "json", "required": False, "group": "extraction"},
            {"param_name": "field_all_separator", "data_type": "string", "required": False, "default_value": " | ", "group": "extraction"},
            {"param_name": "required_field", "data_type": "string", "required": False, "group": "extraction"},
            {"param_name": "next_page_selector", "data_type": "string", "required": False, "group": "pagination"},
            {"param_name": "next_page_attr", "data_type": "string", "required": False, "default_value": "href", "group": "pagination"},
            {"param_name": "max_pages", "data_type": "integer", "required": False, "default_value": 500, "group": "pagination"},
            {"param_name": "delay_between_pages", "data_type": "number", "required": False, "default_value": 1.5, "group": "pagination"},
            {"param_name": "delay_between_pivots", "data_type": "number", "required": False, "default_value": 2.0, "group": "behavior"},
            {"param_name": "stop_on_error", "data_type": "boolean", "required": False, "default_value": False, "group": "behavior"},
            {"param_name": "headers", "data_type": "json", "required": False, "group": "behavior"},
            {"param_name": "timeout", "data_type": "integer", "required": False, "default_value": 30, "group": "behavior"},
        ],
    },
    {
        "name": "XBRL ZIP",
        "class_path": "app.fetchers.xbrl.XbrlFetcher",
        "description": "Generic fetcher for ZIP archives containing XBRL documents.",
        "params": [
            {"param_name": "url", "data_type": "string", "required": True, "group": "http"},
            {"param_name": "method", "data_type": "string", "required": False, "default_value": "GET", "group": "http"},
            {"param_name": "query_params", "data_type": "json", "required": False, "group": "http"},
            {"param_name": "headers", "data_type": "json", "required": False, "group": "http"},
            {"param_name": "timeout", "data_type": "integer", "required": False, "default_value": 120, "group": "http"},
            {"param_name": "xml_pattern", "data_type": "string", "required": False, "group": "zip"},
            {"param_name": "entry", "data_type": "string", "required": False, "group": "zip"},
            {"param_name": "file_classifier", "data_type": "json", "required": False, "group": "zip"},
            {"param_name": "context_fields", "data_type": "json", "required": False, "group": "output"},
            {"param_name": "account_prefix", "data_type": "string", "required": False, "group": "output"},
            {"param_name": "exclude_tags", "data_type": "string", "required": False, "group": "output"},
            {"param_name": "batch_size", "data_type": "integer", "required": False, "default_value": 200, "group": "output"},
        ],
    },
    {
        "name": "PDF_TABLE",
        "class_path": "app.fetchers.pdf_table.PdfTableFetcher",
        "description": "Fetcher for PDFs: iterates a year/month/quarter date range and extracts tables with pdfplumber.",
        "params": [
            {"param_name": "url_template", "data_type": "string", "required": True, "group": "url"},
            {"param_name": "granularity", "data_type": "string", "required": True, "group": "date_range"},
            {"param_name": "year_from", "data_type": "integer", "required": True, "group": "date_range"},
            {"param_name": "year_to", "data_type": "integer", "required": True, "group": "date_range"},
            {"param_name": "table_index", "data_type": "integer", "required": False, "default_value": 0, "group": "extraction"},
            {"param_name": "header_row", "data_type": "integer", "required": False, "default_value": 0, "group": "extraction"},
            {"param_name": "batch_size", "data_type": "integer", "required": False, "default_value": 500, "group": "behavior"},
            {"param_name": "timeout", "data_type": "integer", "required": False, "default_value": 60, "group": "http"},
        ],
    },
    {
        "name": "Web Tree",
        "class_path": "app.fetchers.web_tree_fetcher.WebTreeFetcher",
        "description": "Crawler de portales web clásicos. En modo discover (Resource padre, parent_resource_id=NULL) recorre el árbol e infiere agrupaciones por dimensiones (year, month, quarter, ...) que el operador revisa y promueve. En modo stream (Resource hijo promovido) descarga las URLs de su ResourceCandidate enriqueciendo cada registro con las dimensiones detectadas.",
        "params": [
            {"param_name": "root_url", "data_type": "string", "required": True, "group": "navigation",
             "description": "URL raíz del portal a crawlear. Único parámetro visible — todo lo demás (max_depth, allowed_extensions, timeouts, selectores) son defaults internos del fetcher."},
        ],
    },
]

# ── Catálogo de tecnologías de entrega (especies). Descripción larga con
# explicación y casos de uso. Marcadas como planificadas hasta implementar su clase.
FETCHERS += [{'name': 'GraphQL',
  'class_path': 'app.fetchers.graphql.GraphQLFetcher',
  'description': '⏳ [Tecnología catalogada — implementación de clase pendiente] Consulta declarativa sobre un único '
                 'endpoint: el cliente pide en el cuerpo exactamente los campos que necesita; paginación por '
                 'cursor/connections. Casos de uso: GitHub y Shopify lo popularizaron; en sector público es '
                 'emergente — algunos catálogos y portales de transparencia lo exponen junto a REST; data.europa.eu '
                 'experimenta con endpoints GraphQL.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http'}]},
 {'name': 'SPARQL',
  'class_path': 'app.fetchers.sparql.SparqlFetcher',
  'description': '⏳ [Tecnología catalogada — implementación de clase pendiente] Consulta sobre datos enlazados '
                 '(RDF); los resultados llegan en results.bindings (JSON/XML). Casos de uso: endpoint SPARQL del '
                 'catálogo de datos.gob.es; Aragón Open Data (Linked Data); datos enlazados del BOE (legislación); '
                 'Wikidata, Europeana y el Cellar/EU Vocabularies de la Oficina de Publicaciones de la UE.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http'}]},
 {'name': 'SDMX',
  'class_path': 'app.fetchers.sdmx.SdmxFetcher',
  'description': '⏳ [Tecnología catalogada — implementación de clase pendiente] Estándar de intercambio de datos y '
                 'metadatos ESTADÍSTICOS: dataflows, dimensiones y atributos en SDMX-JSON/XML. Casos de uso: INE '
                 '(API Tempus3/SDMX), Eurostat, Banco de España, Banco Central Europeo, OCDE, FMI y Banco Mundial.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http'}]},
 {'name': 'OAI-PMH',
  'class_path': 'app.fetchers.oai_pmh.OaiPmhFetcher',
  'description': '⏳ [Tecnología catalogada — implementación de clase pendiente] Protocolo de cosecha de metadatos de '
                 "repositorios: verbos ListRecords/ListIdentifiers encadenados por 'resumption token'. Casos de uso: "
                 'Hispana y Europeana (agregación cultural), repositorios universitarios y del CSIC (DSpace), '
                 'TESEO/tesis, Biblioteca Nacional, DataCite y OpenAIRE.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http'}]},
 {'name': 'OGC API - Features',
  'class_path': 'app.fetchers.ogc_features.OgcFeaturesFetcher',
  'description': '⏳ [Tecnología catalogada — implementación de clase pendiente] Sucesor en JSON/GeoJSON de WFS: '
                 "colecciones de entidades geográficas paginadas por enlaces 'next'. Casos de uso: IGN/CNIG y la "
                 'IDEE, Dirección General del Catastro, IDEs autonómicas (ICGC de Cataluña, IDEAndalucía, '
                 'geoEuskadi) y geoportales de data.europa.eu.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http'}]},
 {'name': 'CSW',
  'class_path': 'app.fetchers.csw.CswFetcher',
  'description': '⏳ [Tecnología catalogada — implementación de clase pendiente] Catalogue Service for the Web (OGC): '
                 'catálogo de metadatos geográficos ISO 19139 para descubrir capas y datasets. Casos de uso: '
                 'catálogos INSPIRE del IGN y la IDEE, catálogos de las IDEs autonómicas y municipales, geoportales '
                 'europeos.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http'}]},
 {'name': 'WMTS',
  'class_path': 'app.fetchers.wmts.WmtsFetcher',
  'description': '⏳ [Tecnología catalogada — implementación de clase pendiente] Teselas de mapa precalculadas (OGC '
                 'Web Map Tile Service). Casos de uso: PNOA y ortofotos del IGN, cartografía base de IDEs '
                 'autonómicas y de muchos ayuntamientos.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http'}]},
 {'name': 'WCS',
  'class_path': 'app.fetchers.wcs.WcsFetcher',
  'description': '⏳ [Tecnología catalogada — implementación de clase pendiente] Coberturas ráster (OGC Web Coverage '
                 'Service): datos continuos como elevación o temperatura. Casos de uso: modelos digitales del '
                 'terreno del IGN, mallas climáticas de AEMET y de Copernicus.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http'}]},
 {'name': 'STAC',
  'class_path': 'app.fetchers.stac.StacFetcher',
  'description': '⏳ [Tecnología catalogada — implementación de clase pendiente] SpatioTemporal Asset Catalog: '
                 'catálogo de activos geoespacial-temporales (imágenes de satélite y ortofotos). Casos de uso: '
                 'Copernicus Data Space (Sentinel), PNOA histórico del IGN, y catálogos internacionales (USGS, '
                 'Microsoft Planetary Computer, AWS Open Data).',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http'}]},
 {'name': 'ArcGIS REST',
  'class_path': 'app.fetchers.arcgis.ArcGisFetcher',
  'description': '⏳ [Tecnología catalogada — implementación de clase pendiente] API REST de ArcGIS '
                 '(FeatureServer/MapServer): query?f=json con paginación por resultOffset/resultRecordCount. Casos '
                 'de uso: ubicua en GIS público — visores urbanísticos, callejeros y equipamientos de numerosos '
                 'ayuntamientos y CCAA, y organismos estatales con infraestructura Esri.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http'}]},
 {'name': 'NGSI-LD (FIWARE)',
  'class_path': 'app.fetchers.ngsi_ld.NgsiLdFetcher',
  'description': '⏳ [Tecnología catalogada — implementación de clase pendiente] Datos de contexto en (casi) tiempo '
                 'real en JSON-LD a través de un Context Broker (FIWARE). Casos de uso: ciudades inteligentes '
                 'españolas sobre FIWARE — Santander, Málaga, Valencia, Sevilla — y la Red Española de Ciudades '
                 'Inteligentes (RECI).',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http'}]},
 {'name': 'Server-Sent Events',
  'class_path': 'app.fetchers.sse.SseFetcher',
  'description': '⏳ [Tecnología catalogada — implementación de clase pendiente] Flujo unidireccional '
                 'servidor→cliente sobre HTTP (text/event-stream). Casos de uso: paneles y alertas en vivo, APIs de '
                 'tráfico y movilidad en tiempo real.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http'}]},
 {'name': 'WebSocket',
  'class_path': 'app.fetchers.websocket.WebSocketFetcher',
  'description': '⏳ [Tecnología catalogada — implementación de clase pendiente] Canal bidireccional persistente para '
                 'datos en vivo. Casos de uso: posiciones de transporte, mercados, telemetría de sensores.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http'}]},
 {'name': 'MQTT',
  'class_path': 'app.fetchers.mqtt.MqttFetcher',
  'description': '⏳ [Tecnología catalogada — implementación de clase pendiente] Pub/sub ligero orientado a IoT '
                 '(suscripción a topics de un broker). Casos de uso: sensórica de ciudades inteligentes y medio '
                 'ambiente (calidad del aire, aforo, ruido), habitual en plataformas FIWARE.',
  'params': [{'param_name': 'broker', 'data_type': 'string', 'required': True, 'group': 'http'}]},
 {'name': 'Apache Kafka',
  'class_path': 'app.fetchers.kafka.KafkaFetcher',
  'description': '⏳ [Tecnología catalogada — implementación de clase pendiente] Bus de eventos de alto volumen '
                 '(consumo de topics). Casos de uso: integración interna de grandes administraciones y plataformas '
                 'de datos en tiempo real.',
  'params': [{'param_name': 'brokers', 'data_type': 'string', 'required': True, 'group': 'http'}]},
 {'name': 'GTFS-RT',
  'class_path': 'app.fetchers.gtfs_rt.GtfsRtFetcher',
  'description': '⏳ [Tecnología catalogada — implementación de clase pendiente] Transporte público en tiempo real '
                 '(posiciones, retrasos, incidencias) en protobuf sobre HTTP. Casos de uso: EMT Madrid, TMB '
                 'Barcelona y consorcios de transporte autonómicos; estándar internacional mantenido por '
                 'MobilityData/Google.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http'}]},
 {'name': 'Webhooks entrantes',
  'class_path': 'app.fetchers.webhook_in.WebhookInFetcher',
  'description': '⏳ [Tecnología catalogada — implementación de clase pendiente] La fuente EMPUJA eventos a un '
                 'endpoint que tú expones (push, no pull). Casos de uso: notificaciones de cambios de catálogo y de '
                 'expedientes, integraciones evento-a-evento entre plataformas.',
  'params': [{'param_name': 'endpoint_path', 'data_type': 'string', 'required': True, 'group': 'http'}]},
 {'name': 'Navegador headless',
  'class_path': 'app.fetchers.headless.HeadlessBrowserFetcher',
  'description': '⏳ [Tecnología catalogada — implementación de clase pendiente] Renderiza páginas que cargan sus '
                 'datos por JavaScript (Playwright/Chromium) cuando el scraping HTML estático no ve nada. Casos de '
                 'uso: portales públicos modernos tipo SPA (muchos visores autonómicos y municipales) y aplicaciones '
                 'con tablas alimentadas por una API interna no documentada.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http'}]},
 {'name': 'OCR PDF',
  'class_path': 'app.fetchers.ocr_pdf.OcrPdfFetcher',
  'description': '⏳ [Tecnología catalogada — implementación de clase pendiente] Extrae texto y tablas de PDF que son '
                 'imágenes (sin capa de texto) mediante OCR. Casos de uso: boletines y resoluciones antiguos, BOP '
                 'provinciales escaneados, expedientes digitalizados.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http'}]},
 {'name': 'Documentos ofimáticos',
  'class_path': 'app.fetchers.office_docs.OfficeDocsFetcher',
  'description': '⏳ [Tecnología catalogada — implementación de clase pendiente] Lee tablas y texto de DOCX/XLSX/ODS '
                 'publicados como datos. Casos de uso: anexos de contratación y subvenciones en Excel (p. ej. '
                 'OrganosContratacion.xlsx de PLACSP), memorias y presupuestos en hoja de cálculo.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http'}]},
 {'name': 'Almacenamiento de objetos (S3)',
  'class_path': 'app.fetchers.s3_listing.S3ListingFetcher',
  'description': '⏳ [Tecnología catalogada — implementación de clase pendiente] Lista y descarga volcados masivos de '
                 'un bucket compatible con S3/MinIO. Casos de uso: dumps de datos abiertos en buckets públicos y '
                 'mirrors de datasets grandes (Parquet/CSV), habitual en portales internacionales y data lakes.',
  'params': [{'param_name': 'bucket_url', 'data_type': 'string', 'required': True, 'group': 'http'}]},
 {'name': 'FTP/SFTP/WebDAV',
  'class_path': 'app.fetchers.file_transfer.FileTransferFetcher',
  'description': '⏳ [Tecnología catalogada — implementación de clase pendiente] Transferencia de ficheros por FTP, '
                 'SFTP o WebDAV. Casos de uso: intercambios periódicos entre administraciones y depósitos de '
                 'ficheros estadísticos heredados.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http'}]},
 {'name': 'gRPC',
  'class_path': 'app.fetchers.grpc.GrpcFetcher',
  'description': '⏳ [Tecnología catalogada — implementación de clase pendiente] RPC binario de alto rendimiento '
                 'sobre HTTP/2 (Protocol Buffers). Casos de uso: poco frecuente en datos abiertos; común en '
                 'integraciones internas y entre servicios de plataformas tecnológicas.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http'}]}]


FETCHERS_QUERY = """
query {
  fetchers {
    id
    name
    classPath
    description
    paramsDef {
      id
      paramName
      required
      dataType
      defaultValue
      enumValues
      description
      group
    }
  }
}
"""

CREATE_FETCHER_MUTATION = """
mutation($input: CreateFetcherInput!) {
  createFetcher(input: $input) {
    id
    name
    classPath
    description
  }
}
"""

UPDATE_FETCHER_MUTATION = """
mutation($id: String!, $input: UpdateFetcherInput!) {
  updateFetcher(id: $id, input: $input) {
    id
    name
  }
}
"""

CREATE_PARAM_MUTATION = """
mutation($input: CreateTypeFetcherParamInput!) {
  createTypeFetcherParam(input: $input) {
    id
    paramName
  }
}
"""

DELETE_PARAM_MUTATION = """
mutation($id: String!) {
  deleteTypeFetcherParam(id: $id)
}
"""


def _execute(query: str, variables: Dict[str, Any] | None = None) -> Dict[str, Any]:
    result = schema.execute_sync(query, variable_values=variables)
    if result.errors:
        messages = "; ".join(str(err) for err in result.errors)
        raise RuntimeError(messages)
    return result.data or {}


def _param_payload(param: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "paramName": param["param_name"],
        "required": param.get("required", False),
        "dataType": param.get("data_type", "string"),
    }
    if "default_value" in param:
        payload["defaultValue"] = param.get("default_value")
    if "enum_values" in param:
        payload["enumValues"] = param.get("enum_values")
    if param.get("description") is not None:
        payload["description"] = param.get("description")
    if param.get("group") is not None:
        payload["group"] = param.get("group")
    if param.get("hint") is not None:
        payload["hint"] = param.get("hint")
    if param.get("help_md") is not None:
        payload["helpMd"] = param.get("help_md")
    if param.get("visible_when") is not None:
        payload["visibleWhen"] = param.get("visible_when")
    return payload


def seed() -> None:
    existing = _execute(FETCHERS_QUERY)["fetchers"]
    fetchers_by_name = {item["name"]: item for item in existing}

    for spec in FETCHERS:
        current = fetchers_by_name.get(spec["name"])
        fetcher_input = {
            "name": spec["name"],
            "classPath": spec["class_path"],
            "description": spec.get("description"),
        }

        if current is None:
            created = _execute(CREATE_FETCHER_MUTATION, {"input": fetcher_input})["createFetcher"]
            fetcher_id = created["id"]
            current_params = {}
            print(f"[seed_fetchers] creado fetcher '{spec['name']}'")
        else:
            _execute(UPDATE_FETCHER_MUTATION, {"id": current["id"], "input": fetcher_input})
            fetcher_id = current["id"]
            current_params = {param["paramName"]: param for param in current.get("paramsDef") or []}
            print(f"[seed_fetchers] actualizado fetcher '{spec['name']}'")

        for current_param in current_params.values():
            _execute(DELETE_PARAM_MUTATION, {"id": current_param["id"]})

        for param_spec in spec.get("params", []):
            payload = _param_payload(param_spec)
            payload["fetcherId"] = fetcher_id
            _execute(CREATE_PARAM_MUTATION, {"input": payload})

    # Persistir los bloques preset_params (variantes) vía ORM directo.
    presets = {sp["name"]: sp["preset_params"] for sp in FETCHERS if sp.get("preset_params")}
    if presets:
        from app.database import SessionLocal
        from app.models import Fetcher
        db = SessionLocal()
        try:
            for code, preset in presets.items():
                f = db.query(Fetcher).filter(Fetcher.code == code).first()
                if f:
                    f.preset_params = preset
            db.commit()
            print(f"[seed_fetchers] preset_params aplicados a {len(presets)} variante(s)")
        finally:
            db.close()

    # Fusión de la familia REST: las variantes históricas (paginada / loop / time
    # series) son ya la especie 'API REST' con distintas elecciones de petición,
    # paginación y extracción. Repuntamos sus recursos a 'API REST' añadiendo los
    # params mapeados y retiramos las filas variantes. Idempotente (tras la 1ª pasada
    # no quedan recursos en las variantes ni filas sin retirar).
    from app.database import SessionLocal
    from app.models import Fetcher, Resource, ResourceParam
    from datetime import datetime
    _MAP_REST = {
        "API REST Paginada": {"pagination": "page_number", "start_page": "0", "request": "query", "extraction": "passthrough"},
        "REST Loop": {"request": "json_body", "pagination": "pivot_loop", "extraction": "passthrough"},
        "JSON Time Series": {"request": "query", "pagination": "none", "extraction": "timeseries_long"},
    }
    db = SessionLocal()
    try:
        api = db.query(Fetcher).filter(Fetcher.code == "API REST").first()
        migrados, retirados = 0, []
        if api:
            for code, extra in _MAP_REST.items():
                f = db.query(Fetcher).filter(Fetcher.code == code).first()
                if not f:
                    continue
                for r in db.query(Resource).filter(Resource.fetcher_id == f.id).all():
                    claves = {p.key for p in db.query(ResourceParam).filter(ResourceParam.resource_id == r.id).all()}
                    if code == "JSON Time Series" and "content_field" not in claves:
                        rp = db.query(ResourceParam).filter(ResourceParam.resource_id == r.id, ResourceParam.key == "root_path").first()
                        if rp and rp.value:
                            db.add(ResourceParam(resource_id=r.id, key="content_field", value=rp.value, is_external=False))
                            claves.add("content_field")
                    for k, v in extra.items():
                        if k not in claves:
                            db.add(ResourceParam(resource_id=r.id, key=k, value=v, is_external=False))
                    r.fetcher_id = api.id
                    migrados += 1
                if f.deleted_at is None:
                    f.deleted_at = datetime.utcnow()
                    retirados.append(code)
            if migrados or retirados:
                db.commit()
                print(f"[seed_fetchers] familia REST fusionada en 'API REST': {migrados} recurso(s); retiradas {retirados}")
    finally:
        db.close()

    # Poda segura: retira filas de fetcher MUERTAS (clase no importable) y sin
    # recursos. Enacta "un fetcher solo existe por una tecnología real": lo que no
    # tiene clase ni uso no es una tecnología, es ruido. Las tecnologías legítimas
    # sin recursos NO se tocan (esperan un recurso que las valide).
    import importlib
    from app.database import SessionLocal
    from app.models import Fetcher
    db = SessionLocal()
    try:
        retirados = []
        seeded = {sp["name"] for sp in FETCHERS}
        for f in db.query(Fetcher).filter(Fetcher.deleted_at.is_(None)).all():
            if f.code in seeded:   # del catálogo de tecnologías → intocable
                continue
            if f.resources:  # tiene recursos → intocable
                continue
            cp = f.class_path
            importable = False
            if cp:
                try:
                    mod, cls = cp.rsplit(".", 1)
                    importable = hasattr(importlib.import_module(mod), cls)
                except Exception:
                    importable = False
            if not importable:
                from datetime import datetime
                f.deleted_at = datetime.utcnow()
                retirados.append(f.code)
        if retirados:
            db.commit()
            print(f"[seed_fetchers] retirados (muertos, sin clase ni recursos): {retirados}")
    finally:
        db.close()

    print(f"[seed_fetchers] catálogo sincronizado: {len(FETCHERS)} fetchers base")


if __name__ == "__main__":
    try:
        seed()
    except Exception as exc:
        print(f"[seed_fetchers] ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
