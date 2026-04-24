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
        "description": "RESTful API with JSON/XML support",
        "params": [
            {"param_name": "url", "data_type": "string", "required": True, "group": "http"},
            {"param_name": "method", "data_type": "string", "required": False, "default_value": "GET", "group": "http"},
            {"param_name": "headers", "data_type": "json", "required": False, "group": "http"},
            {"param_name": "query_params", "data_type": "json", "required": False, "group": "http"},
            {"param_name": "timeout", "data_type": "integer", "required": False, "default_value": 30, "group": "http"},
            {"param_name": "max_retries", "data_type": "integer", "required": False, "default_value": 3, "group": "http"},
        ],
    },
    {
        "name": "API REST Paginada",
        "class_path": "app.fetchers.paginated_rest.PaginatedRestFetcher",
        "description": "Paginated REST API — iterates pages until empty",
        "params": [
            {"param_name": "url", "data_type": "string", "required": True, "group": "http"},
            {"param_name": "method", "data_type": "string", "required": False, "default_value": "GET", "group": "http"},
            {"param_name": "timeout", "data_type": "integer", "required": False, "default_value": 60, "group": "http"},
            {"param_name": "id_field", "data_type": "string", "required": False, "group": "pagination"},
            {"param_name": "bounding_field", "data_type": "string", "required": False, "group": "pagination"},
        ],
    },
    {
        "name": "Feeds ATOM/RSS",
        "class_path": "app.fetchers.atom.AtomFetcher",
        "description": "ATOM/RSS feed reader",
        "params": [
            {"param_name": "url", "data_type": "string", "required": True, "group": "http"},
            {"param_name": "max_items", "data_type": "integer", "required": False, "default_value": 1000, "group": "behavior"},
        ],
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
            {"param_name": "url", "data_type": "string", "required": True, "group": "navigation"},
            {"param_name": "levels", "data_type": "json", "required": True, "group": "navigation"},
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
        "name": "REST Loop",
        "class_path": "app.fetchers.rest_loop.RestLoopFetcher",
        "description": "REST API iterated over a list of pivot values (e.g. province codes)",
        "params": [
            {"param_name": "url", "data_type": "string", "required": True, "group": "http"},
            {"param_name": "method", "data_type": "string", "required": False, "default_value": "POST", "group": "http"},
            {"param_name": "payload_template", "data_type": "json", "required": False, "group": "http"},
            {"param_name": "pivot_values", "data_type": "json", "required": False, "group": "pivot"},
            {"param_name": "id_field", "data_type": "string", "required": False, "group": "behavior"},
            {"param_name": "delay", "data_type": "number", "required": False, "default_value": 2, "group": "behavior"},
            {"param_name": "timeout", "data_type": "integer", "required": False, "default_value": 30, "group": "http"},
            {"param_name": "headers", "data_type": "json", "required": False, "group": "http"},
        ],
    },
    {
        "name": "JSON Time Series",
        "class_path": "app.fetchers.json_timeseries.JsonTimeseriesFetcher",
        "description": "Generic fetcher for APIs that return arrays of time series with metadata.",
        "params": [
            {"param_name": "url", "data_type": "string", "required": True, "group": "http"},
            {"param_name": "method", "data_type": "string", "required": False, "default_value": "GET", "group": "http"},
            {"param_name": "query_params", "data_type": "json", "required": False, "group": "http"},
            {"param_name": "headers", "data_type": "json", "required": False, "group": "http"},
            {"param_name": "timeout", "data_type": "integer", "required": False, "default_value": 120, "group": "http"},
            {"param_name": "root_path", "data_type": "string", "required": False, "group": "structure"},
            {"param_name": "meta_container", "data_type": "string", "required": False, "default_value": "MetaData", "group": "structure"},
            {"param_name": "meta_code_field", "data_type": "string", "required": False, "default_value": "Codigo", "group": "structure"},
            {"param_name": "meta_name_field", "data_type": "string", "required": False, "default_value": "Nombre", "group": "structure"},
            {"param_name": "meta_dim_path", "data_type": "string", "required": False, "default_value": "Variable.Codigo", "group": "structure"},
            {"param_name": "data_container", "data_type": "string", "required": False, "default_value": "Data", "group": "structure"},
            {"param_name": "period_field", "data_type": "string", "required": False, "default_value": "Anyo", "group": "structure"},
            {"param_name": "subperiod_field", "data_type": "string", "required": False, "default_value": "Periodo", "group": "structure"},
            {"param_name": "value_field", "data_type": "string", "required": False, "default_value": "Valor", "group": "structure"},
            {"param_name": "secret_field", "data_type": "string", "required": False, "default_value": "Secreto", "group": "structure"},
            {"param_name": "serie_name_field", "data_type": "string", "required": False, "default_value": "Nombre", "group": "structure"},
            {"param_name": "flatten_mode", "data_type": "string", "required": False, "default_value": "long", "group": "output"},
            {"param_name": "batch_size", "data_type": "integer", "required": False, "default_value": 500, "group": "output"},
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
        "name": "Portal Documental",
        "class_path": "app.fetchers.legacy_data_portal.LegacyDataPortalFetcher",
        "description": "Crawler genérico para portales con árboles de páginas y artefactos descargables heterogéneos.",
        "params": [
            {"param_name": "start_url", "data_type": "string", "required": False, "group": "navigation"},
            {"param_name": "start_urls", "data_type": "json", "required": False, "group": "navigation"},
            {"param_name": "max_depth", "data_type": "integer", "required": False, "default_value": 0, "group": "navigation"},
            {"param_name": "same_domain_only", "data_type": "boolean", "required": False, "default_value": True, "group": "navigation"},
            {"param_name": "navigation_link_selector", "data_type": "string", "required": False, "group": "navigation"},
            {"param_name": "navigation_link_attr", "data_type": "string", "required": False, "default_value": "href", "group": "navigation"},
            {"param_name": "page_include_patterns", "data_type": "json", "required": False, "group": "navigation"},
            {"param_name": "page_exclude_patterns", "data_type": "json", "required": False, "group": "navigation"},
            {"param_name": "file_link_selector", "data_type": "string", "required": False, "group": "file_discovery"},
            {"param_name": "file_link_attr", "data_type": "string", "required": False, "default_value": "href", "group": "file_discovery"},
            {"param_name": "allowed_extensions", "data_type": "json", "required": False, "group": "file_discovery"},
            {"param_name": "file_include_patterns", "data_type": "json", "required": False, "group": "file_discovery"},
            {"param_name": "file_exclude_patterns", "data_type": "json", "required": False, "group": "file_discovery"},
            {"param_name": "format_overrides", "data_type": "json", "required": False, "group": "file_discovery"},
            {"param_name": "page_context_selectors", "data_type": "json", "required": False, "group": "context"},
            {"param_name": "page_context_attr_selectors", "data_type": "json", "required": False, "group": "context"},
            {"param_name": "inherit_context_fields", "data_type": "json", "required": False, "group": "context"},
            {"param_name": "common_parser_options", "data_type": "json", "required": False, "group": "parsing"},
            {"param_name": "parser_options", "data_type": "json", "required": False, "group": "parsing"},
            {"param_name": "headers", "data_type": "json", "required": False, "group": "http"},
            {"param_name": "timeout", "data_type": "integer", "required": False, "default_value": 60, "group": "http"},
            {"param_name": "batch_size", "data_type": "integer", "required": False, "default_value": 500, "group": "behavior"},
            {"param_name": "page_delay", "data_type": "number", "required": False, "default_value": 0, "group": "behavior"},
            {"param_name": "file_delay", "data_type": "number", "required": False, "default_value": 0, "group": "behavior"},
        ],
    },
    {
        "name": "Portal Files Cataloguer",
        "class_path": "app.fetchers.portal_files_cataloguer.PortalFilesCataloguer",
        "description": "Meta-fetcher que cataloga los ficheros descargables de un portal clasificándolos por análisis del path en section_id jerárquico y atributos (ejercicio, trimestre…). Cada fila es un fichero del portal. El catálogo resultante alimenta a los PortalFileDataFetcher.",
        "params": [
            {"param_name": "start_url", "data_type": "string", "required": False, "group": "navigation"},
            {"param_name": "start_urls", "data_type": "json", "required": False, "group": "navigation"},
            {"param_name": "max_depth", "data_type": "integer", "required": False, "default_value": 10, "group": "navigation"},
            {"param_name": "same_domain_only", "data_type": "boolean", "required": False, "default_value": True, "group": "navigation"},
            {"param_name": "navigation_link_selector", "data_type": "string", "required": False, "group": "navigation"},
            {"param_name": "navigation_link_attr", "data_type": "string", "required": False, "default_value": "href", "group": "navigation"},
            {"param_name": "page_include_patterns", "data_type": "json", "required": False, "group": "navigation"},
            {"param_name": "page_exclude_patterns", "data_type": "json", "required": False, "group": "navigation"},
            {"param_name": "file_link_selector", "data_type": "string", "required": False, "group": "file_discovery"},
            {"param_name": "file_link_attr", "data_type": "string", "required": False, "default_value": "href", "group": "file_discovery"},
            {"param_name": "allowed_extensions", "data_type": "json", "required": False, "group": "file_discovery"},
            {"param_name": "file_include_patterns", "data_type": "json", "required": False, "group": "file_discovery"},
            {"param_name": "file_exclude_patterns", "data_type": "json", "required": False, "group": "file_discovery"},
            {"param_name": "path_prefix_strip", "data_type": "string", "required": False, "group": "classification"},
            {"param_name": "segment_prefix_strip_pattern", "data_type": "string", "required": False, "group": "classification"},
            {"param_name": "noise_segments", "data_type": "json", "required": False, "group": "classification"},
            {"param_name": "attribute_patterns", "data_type": "json", "required": False, "group": "classification"},
            {"param_name": "filename_attribute_patterns", "data_type": "json", "required": False, "group": "classification"},
            {"param_name": "headers", "data_type": "json", "required": False, "group": "http"},
            {"param_name": "crawl_timeout", "data_type": "integer", "required": False, "default_value": 15, "group": "http"},
            {"param_name": "batch_size", "data_type": "integer", "required": False, "default_value": 500, "group": "behavior"},
            {"param_name": "page_delay", "data_type": "number", "required": False, "default_value": 0, "group": "behavior"},
        ],
    },
]


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

    print(f"[seed_fetchers] catálogo sincronizado: {len(FETCHERS)} fetchers base")


if __name__ == "__main__":
    try:
        seed()
    except Exception as exc:
        print(f"[seed_fetchers] ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
