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
            {"param_name": "pagination", "data_type": "enum", "required": False, "default_value": "none", "group": "paginacion",
             "hint": "Cómo se recorre el conjunto cuando viene repartido en páginas.",
             "enum_values": [
                 {"value": "none", "label": "Sin paginación", "help": "Una sola petición; la respuesta se guarda tal cual."},
                 {"value": "query_offset", "label": "Offset/límite", "help": "Avanza con parámetros offset/limit en la query."},
                 {"value": "page_number", "label": "Número de página", "help": "Incrementa un parámetro de página (1, 2, 3...)."},
                 {"value": "rel_next", "label": "Enlace 'siguiente'", "help": "Sigue el enlace a la página siguiente que devuelve la propia respuesta."},
                 {"value": "cursor", "label": "Cursor", "help": "Reenvía el token de continuación que devuelve cada página."},
                 {"value": "pivot_loop", "label": "Una petición por valor", "help": "Repite la petición para cada valor de una lista (provincias, códigos...)."},
             ]},
            {"param_name": "content_field", "data_type": "string", "required": False, "group": "extraccion",
             "hint": "Ruta (con puntos) a la lista de registros en cada página, p. ej. 'content' o 'data.items'."},
            {"param_name": "extraction", "data_type": "enum", "required": False, "default_value": "passthrough", "group": "extraccion",
             "hint": "Cómo se convierte la respuesta en registros planos.",
             "enum_values": [
                 {"value": "passthrough", "label": "Tal cual", "help": "Los registros como vienen, sin aplanar."},
                 {"value": "field_map", "label": "Mapa de campos", "help": "Aplana cada registro con {campo_salida: ruta.con.puntos}."},
                 {"value": "timeseries_long", "label": "Series temporales (formato largo)", "help": "APIs estadísticas tipo INE: una fila por punto, con sus dimensiones."},
                 {"value": "bindings", "label": "Resultados SPARQL", "help": "Aplana results.bindings a {variable: valor}."},
             ]},
            {"param_name": "field_map", "data_type": "json", "required": False, "group": "extraccion", "visible_when": {"param": "extraction", "in": ["field_map"]},
             "hint": "Para extraction=field_map: {campo_salida: ruta.con.puntos}."},
            {"param_name": "page_size", "data_type": "integer", "required": False, "group": "paginacion", "visible_when": {"param": "pagination", "in": ["query_offset", "page_number"]}},
            {"param_name": "next_link_field", "data_type": "string", "required": False, "group": "paginacion", "visible_when": {"param": "pagination", "in": ["rel_next"]},
             "hint": "Para pagination=rel_next sobre JSON: ruta al enlace de la siguiente página."},
            {"param_name": "cursor_field", "data_type": "string", "required": False, "group": "paginacion", "visible_when": {"param": "pagination", "in": ["cursor"]},
             "hint": "Para pagination=cursor: ruta al token de la siguiente página en la respuesta."},
            {"param_name": "request", "data_type": "enum", "required": False, "default_value": "query", "group": "peticion",
             "hint": "Qué se envía en cada petición.",
             "enum_values": [
                 {"value": "query", "label": "Solo parámetros de URL", "help": "GET (o el método indicado) sin cuerpo."},
                 {"value": "json_body", "label": "Cuerpo JSON", "help": "POST con un cuerpo JSON de plantilla; admite {pivot}."},
                 {"value": "form", "label": "Formulario", "help": "POST con cuerpo de formulario (urlencoded)."},
                 {"value": "graphql", "label": "Consulta GraphQL", "help": "POST {query, variables}; escribe la consulta en 'query'."},
                 {"value": "sparql", "label": "Consulta SPARQL", "help": "Envía 'query=...' y pide resultados JSON; escribe la consulta en 'query'."},
             ]},
            {"param_name": "payload_template", "data_type": "json", "required": False, "group": "peticion", "visible_when": {"param": "request", "in": ["json_body", "form"]},
             "hint": "Para request=json_body/form: plantilla de cuerpo; usa {pivot} para el valor iterado (pagination=pivot_loop)."},
            {"param_name": "pivot_param", "data_type": "string", "required": False, "group": "paginacion", "visible_when": {"param": "pagination", "in": ["pivot_loop"]},
             "hint": "Para pagination=pivot_loop: nombre del parámetro/marcador del valor iterado."},
            {"param_name": "pivot_values", "data_type": "json", "required": False, "group": "paginacion", "visible_when": {"param": "pagination", "in": ["pivot_loop"]},
             "hint": "Para pagination=pivot_loop: lista de valores a iterar (una petición por valor)."},
            {"param_name": "query", "data_type": "string", "required": False, "group": "peticion",
             "hint": "Texto de la consulta; su lenguaje lo decide 'request' (GraphQL o SPARQL). Se valida la sintaxis al guardar el recurso.",
             "visible_when": {"param": "request", "in": ["graphql", "sparql"]}},
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
        "name": "Power BI",
        "class_path": "app.fetchers.powerbi.PowerBIFetcher",
        "description": "Extrae datos de reports públicos de Power BI (los paneles embebidos que publican muchos organismos). Lee cualquier visual del report usando la API pública de querydata, con paginación automática por restart tokens y decodificación del formato DSR. Necesita los identificadores del report embebido (resource_key, model_id, dataset_id, report_id, visual_id) y la consulta semántica (query_json). Caso de uso documentado: Registro de Entidades Religiosas (config_rer.md).",
        "params": [
            {"param_name": "resource_key", "data_type": "string", "required": True, "group": "http",
             "hint": "X-PowerBI-ResourceKey: campo 'k' del token del embed público."},
            {"param_name": "model_id", "data_type": "integer", "required": True, "group": "peticion"},
            {"param_name": "dataset_id", "data_type": "string", "required": True, "group": "peticion"},
            {"param_name": "report_id", "data_type": "string", "required": True, "group": "peticion"},
            {"param_name": "visual_id", "data_type": "string", "required": False, "default_value": "powerbi_fetcher", "group": "peticion",
             "hint": "Cualquier ID de visual válido del report; la clase usa un valor por defecto si no se indica."},
            {"param_name": "query_json", "data_type": "json", "required": True, "group": "peticion",
             "hint": "SemanticQuery completa: {From:[...], Select:[...], Where:[...], OrderBy:[...]}."},
            {"param_name": "projections", "data_type": "string", "required": False, "group": "extraccion",
             "hint": "Índices de proyección separados por coma, p. ej. '0,1,2'."},
            {"param_name": "field_mapping", "data_type": "json", "required": False, "group": "extraccion",
             "hint": "Mapa Gn → nombre de campo, p. ej. {\"G0\": \"nombre\", \"G1\": \"web\"}. Sin definir: G0, G1, ..."},
            {"param_name": "page_size", "data_type": "integer", "required": False, "default_value": 500, "group": "paginacion"},
            {"param_name": "delay", "data_type": "number", "required": False, "default_value": 0.3, "group": "behavior"},
            {"param_name": "timeout", "data_type": "integer", "required": False, "default_value": 60, "group": "http"},
        ],
    },
    {
        "name": "HTML (genérico)",
        "class_path": "app.fetchers.html_generic.HTMLFetcher",
        "description": "ESPECIE genérica de scraping HTML sobre HTTP. Delega en registros: navegación (single|paged|pivot|form_pivot), extracción (fields|table, dialecto de selectores CSS) y construcción de la petición (query|form_submit). Absorbe HTML Forms, HTML Paginated y URL Loop HTML.",
        "params": [
            {"param_name": "url", "data_type": "string", "required": False, "group": "http"},
            {"param_name": "url_template", "data_type": "string", "required": False, "group": "navegacion",
             "hint": "Plantilla con {value} (pivote) y/o {page} (paginación).",
             "visible_when": {"param": "navigation", "in": ["paged", "pivot"]}},
            {"param_name": "navigation", "data_type": "enum", "required": False, "default_value": "single", "group": "navegacion",
             "hint": "Cómo se recorre el sitio.",
             "enum_values": [
                 {"value": "single", "label": "Una sola página", "help": "Descarga 'url' y extrae."},
                 {"value": "paged", "label": "Paginado", "help": "Sigue la paginación (enlace 'siguiente' o {page} en la plantilla)."},
                 {"value": "pivot", "label": "Una búsqueda por valor", "help": "Repite la consulta para cada valor de una lista; admite paginación dentro de cada valor."},
                 {"value": "form_pivot", "label": "Formulario por valor", "help": "Descubre el formulario (campos ocultos + action) y lo envía por cada valor."},
                 {"value": "form_paged", "label": "Formulario paginado", "help": "Re-envía el formulario de paginación incrementando el parámetro de página, con sesión (buscadores con estado)."},
             ]},
            {"param_name": "extraction", "data_type": "enum", "required": False, "default_value": "fields", "group": "extraccion",
             "hint": "Cómo se leen los datos de cada página.",
             "enum_values": [
                 {"value": "fields", "label": "Campos por selectores", "help": "Un registro por fila (rows_selector) con selectores CSS por campo."},
                 {"value": "table", "label": "Tabla", "help": "Vuelca una tabla HTML (cabecera + celdas) a registros."},
             ]},
            {"param_name": "request", "data_type": "enum", "required": False, "default_value": "query", "group": "peticion",
             "hint": "Qué se envía en cada petición.",
             "enum_values": [
                 {"value": "query", "label": "Solo parámetros de URL", "help": "GET sin cuerpo."},
                 {"value": "form_submit", "label": "Envío de formulario", "help": "POST con los campos ocultos descubiertos + el campo de búsqueda."},
             ]},
            {"param_name": "rows_selector", "data_type": "string", "required": False, "group": "extraccion", "hint": "Selector CSS de cada fila/registro (en 'table', de las filas de la tabla)."},
            {"param_name": "field_selectors", "data_type": "json", "required": False, "group": "extraccion", "visible_when": {"param": "extraction", "in": ["fields"]}},
            {"param_name": "field_attr_selectors", "data_type": "json", "required": False, "group": "extraccion", "visible_when": {"param": "extraction", "in": ["fields"]}},
            {"param_name": "field_all_selectors", "data_type": "json", "required": False, "group": "extraccion", "visible_when": {"param": "extraction", "in": ["fields"]}},
            {"param_name": "field_all_text", "data_type": "json", "required": False, "group": "extraccion", "visible_when": {"param": "extraction", "in": ["fields"]}},
            {"param_name": "field_attrs", "data_type": "json", "required": False, "group": "extraccion", "visible_when": {"param": "extraction", "in": ["fields"]}},
            {"param_name": "field_label_selectors", "data_type": "json", "required": False, "group": "extraccion", "visible_when": {"param": "extraction", "in": ["fields"]}},
            {"param_name": "next_page_selector", "data_type": "string", "required": False, "group": "navegacion", "visible_when": {"param": "navigation", "in": ["paged", "pivot"]}},
            {"param_name": "next_page_attr", "data_type": "string", "required": False, "default_value": "href", "group": "navegacion", "visible_when": {"param": "navigation", "in": ["paged", "pivot"]}},
            {"param_name": "pivot_values", "data_type": "json", "required": False, "group": "navegacion", "visible_when": {"param": "navigation", "in": ["pivot", "form_pivot"]}},
            {"param_name": "search_field_values", "data_type": "json", "required": False, "group": "navegacion", "visible_when": {"param": "navigation", "in": ["pivot", "form_pivot"]}},
            {"param_name": "search_field_name", "data_type": "string", "required": False, "group": "navegacion", "visible_when": {"param": "navigation", "in": ["form_pivot"]}},
            {"param_name": "form_selector", "data_type": "string", "required": False, "group": "navegacion", "visible_when": {"param": "navigation", "in": ["form_pivot"]}},
            {"param_name": "next_form_selector", "data_type": "string", "required": False, "group": "navegacion",
             "hint": "Selector(es) CSS del formulario de paginación (admite lista separada por comas).",
             "visible_when": {"param": "navigation", "in": ["form_paged"]}},
            {"param_name": "page_param", "data_type": "string", "required": False, "default_value": "pagina", "group": "navegacion",
             "visible_when": {"param": "navigation", "in": ["form_paged"]}},
            {"param_name": "pivot_source_odmgr_query", "data_type": "string", "required": False, "group": "navegacion", "visible_when": {"param": "navigation", "in": ["pivot"]}},
            {"param_name": "pivot_source_field", "data_type": "string", "required": False, "group": "navegacion", "visible_when": {"param": "navigation", "in": ["pivot"]}},
            {"param_name": "max_pages", "data_type": "integer", "required": False, "default_value": 500, "group": "navegacion", "visible_when": {"param": "navigation", "in": ["paged", "pivot"]}},
            {"param_name": "start_page", "data_type": "integer", "required": False, "default_value": 1, "group": "navegacion", "visible_when": {"param": "navigation", "in": ["paged", "pivot"]}},
            {"param_name": "delay_between_pages", "data_type": "number", "required": False, "default_value": 1.0, "group": "behavior"},
            {"param_name": "headers", "data_type": "json", "required": False, "group": "http"},
            {"param_name": "timeout", "data_type": "integer", "required": False, "default_value": 30, "group": "http"},
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


# Contexto de arranque: el seed corre en proceso, antes de la app, con acceso
# directo a la BD; no es una petición de usuario. Se otorga a sí mismo los permisos
# del catálogo para pasar las permission_classes de las mutaciones. La vía HTTP
# (get_graphql_context) no se toca: sigue exigiendo sesión autenticada.
from app.rbac import MAPA_TRANSACCIONES as _MAPA_TX
_CTX_BOOTSTRAP: Dict[str, Any] = {"permisos": set(_MAPA_TX.values()), "username": "bootstrap"}


def _execute(query: str, variables: Dict[str, Any] | None = None) -> Dict[str, Any]:
    result = schema.execute_sync(query, variable_values=variables, context_value=_CTX_BOOTSTRAP)
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

    # Fusión de la familia HTML mecánica (Forms / Paginated / URL Loop) en la especie
    # 'HTML (genérico)'. Mapeo por clase del modo de navegación y la estrategia de
    # extracción; los selectores bespoke ya viven en cada recurso. Idempotente.
    # (searchloop/web_tree NO se tocan: recursión por niveles y árbol son especies propias.)
    _MAP_HTML = {
        "HTML Forms": {"navigation": "single", "extraction": "table", "request": "query"},
        "HTML Paginated": {"navigation": "paged", "extraction": "fields", "request": "query"},
        "URL Loop HTML": {"navigation": "pivot", "extraction": "fields", "request": "query"},
    }
    from app.database import SessionLocal as _SL_H
    from app.models import Fetcher as _F_H, Resource as _R_H, ResourceParam as _RP_H
    from datetime import datetime as _dt_H
    db = _SL_H()
    try:
        gen = db.query(_F_H).filter(_F_H.code == "HTML (genérico)").first()
        mig, ret = 0, []
        if gen:
            for code, extra in _MAP_HTML.items():
                f = db.query(_F_H).filter(_F_H.code == code).first()
                if not f:
                    continue
                for r in db.query(_R_H).filter(_R_H.fetcher_id == f.id).all():
                    claves = {p.key for p in db.query(_RP_H).filter(_RP_H.resource_id == r.id).all()}
                    for k, v in extra.items():
                        if k not in claves:
                            db.add(_RP_H(resource_id=r.id, key=k, value=v, is_external=False))
                    r.fetcher_id = gen.id
                    mig += 1
                if f.deleted_at is None:
                    f.deleted_at = _dt_H.utcnow()
                    ret.append(code)
            if mig or ret:
                db.commit()
                print(f"[seed_fetchers] familia HTML mecánica fusionada en 'HTML (genérico)': {mig} recurso(s); retiradas {ret}")
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

    # Fidelidad de la fusión HTML: los recursos que paginaban por re-envío de
    # formulario (pagination_type=form, p. ej. RER) deben usar navigation=form_paged,
    # no 'paged' (que pagina por enlace). Idempotente.
    db = _SL_H()
    try:
        corregidos = 0
        for rp in db.query(_RP_H).filter(_RP_H.key == "pagination_type", _RP_H.value == "form").all():
            nav = db.query(_RP_H).filter(_RP_H.resource_id == rp.resource_id, _RP_H.key == "navigation").first()
            if nav is None:
                db.add(_RP_H(resource_id=rp.resource_id, key="navigation", value="form_paged", is_external=False))
                corregidos += 1
            elif nav.value != "form_paged":
                nav.value = "form_paged"
                corregidos += 1
        if corregidos:
            db.commit()
            print(f"[seed_fetchers] navegación corregida a form_paged en {corregidos} recurso(s) con paginación por formulario")
    finally:
        db.close()

    # Rebaseline de sincronización: las fusiones (y cualquier transformación de
    # sistema) cambian recursos en BD sin pasar por la UI ni por un manifiesto, así
    # que su hash canónico queda desincronizado de last_synced_hash y los updates de
    # manifiesto entrarían en conflicto. registrar_version no-opea si no hay deriva;
    # si la hay, versiona el estado real de la BD y lo convierte en la nueva base.
    from app.services.manifests import registrar_version as _rv
    db = _SL_H()
    try:
        rebaselined = 0
        for r in db.query(_R_H).filter(_R_H.deleted_at.is_(None)).all():
            try:
                if _rv(db, r, origin="seed", author="rebaseline"):
                    rebaselined += 1
            except Exception as e:
                print(f"[seed_fetchers] AVISO rebaseline '{getattr(r, 'name', r.id)}': {e}")
        if rebaselined:
            db.commit()
            print(f"[seed_fetchers] rebaseline: {rebaselined} recurso(s) re-sincronizados tras transformaciones de sistema")
    finally:
        db.close()

    # Reset del historial de versiones (una sola vez): el historial acumulado
    # durante el refactor de la aplicación (fusiones, rebaselines, correcciones de
    # manifiesto) es ruido de sistema, no historia editorial de los recursos. Se
    # borra y cada recurso arranca en versión 1 con su estado actual como base.
    # Autodesarmable: la presencia del marcador (author='reset-historial-v1') hace
    # que no vuelva a ejecutarse; el historial legítimo posterior se conserva.
    from app.models import ResourceManifestVersion as _RMV
    from app.services.manifests import _canonical_from_db as _canon_db, manifest_hash as _mh
    db = _SL_H()
    try:
        ya_reseteado = db.query(_RMV).filter(_RMV.author == "reset-historial-v1").first() is not None
        hay_historial = db.query(_RMV).first() is not None
        if hay_historial and not ya_reseteado:
            borradas = db.query(_RMV).delete()
            nuevos = 0
            for r in db.query(_R_H).filter(_R_H.deleted_at.is_(None)).all():
                try:
                    canon = _canon_db(db, r)
                    h = _mh(canon)
                    r.manifest_version = 1
                    r.manifest_hash = h
                    r.last_synced_hash = h
                    db.add(_RMV(resource_id=r.id, version=1, manifest_json=canon, hash=h,
                                origin="seed", author="reset-historial-v1"))
                    nuevos += 1
                except Exception as e:
                    print(f"[seed_fetchers] AVISO reset historial '{getattr(r, 'name', r.id)}': {e}")
            db.commit()
            print(f"[seed_fetchers] historial de versiones reseteado: {borradas} entradas antiguas eliminadas, {nuevos} recursos en versión 1")
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
