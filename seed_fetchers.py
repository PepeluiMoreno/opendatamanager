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
        "name": "Headless (navegador)",
        "class_path": "app.fetchers.headless.HeadlessFetcher",
        "description": "Renderizado JS con navegador headless (Playwright). Para fuentes cuyo dato solo existe tras ejecutar JavaScript: correos ofuscados (Joomla email cloaking, Cloudflare data-cfemail, reensamblado por script) y listados AJAX. Itera sobre una o varias URLs y, opcionalmente, salta un nivel a páginas internas de contacto/directorio.",
        "params": [
            {"param_name": "url", "data_type": "string", "required": False, "group": "fuente", "hint": "URL única a renderizar. Alternativa a 'urls' o 'url_template'."},
            {"param_name": "urls", "data_type": "json", "required": False, "group": "fuente", "hint": "Lista JSON de URLs semilla. Ej.: [\"https://a.org/\", \"https://b.es/\"]"},
            {"param_name": "url_template", "data_type": "string", "required": False, "group": "fuente", "hint": "Plantilla con {value}; se combina con pivot_values."},
            {"param_name": "pivot_values", "data_type": "json", "required": False, "group": "fuente", "hint": "Lista JSON de valores para sustituir {value} en url_template."},
            {"param_name": "extract", "data_type": "enum", "required": False, "default_value": "emails", "group": "extraccion",
             "hint": "Qué extraer del DOM renderizado.",
             "enum_values": [
                 {"value": "emails", "label": "Correos", "help": "Un registro por (url, email): mailto + data-cfemail (+texto opcional)."},
                 {"value": "fields", "label": "Campos CSS", "help": "Un registro por URL con field_selectors aplicados sobre el DOM ya renderizado."},
             ]},
            {"param_name": "follow_keywords", "data_type": "string", "required": False, "default_value": "contacto,contact,directorio,curia,secretaria,delegacion,equipo,organigrama", "group": "navegacion", "hint": "Palabras clave (CSV) en enlaces a seguir UN nivel desde cada semilla."},
            {"param_name": "max_follow", "data_type": "integer", "required": False, "default_value": 6, "group": "navegacion", "hint": "Máx. subpáginas a seguir por semilla. 0 = no seguir."},
            {"param_name": "same_domain_only", "data_type": "boolean", "required": False, "default_value": True, "group": "navegacion", "hint": "Seguir solo enlaces del mismo dominio que la semilla."},
            {"param_name": "wait_until", "data_type": "string", "required": False, "default_value": "networkidle", "group": "render", "hint": "Evento de carga: load | domcontentloaded | networkidle."},
            {"param_name": "page_timeout_ms", "data_type": "integer", "required": False, "default_value": 45000, "group": "render", "hint": "Timeout de navegación por página, en ms."},
            {"param_name": "block_assets", "data_type": "boolean", "required": False, "default_value": True, "group": "render", "hint": "Bloquea imágenes/fuentes/CSS para acelerar el render."},
            {"param_name": "text_emails", "data_type": "boolean", "required": False, "default_value": False, "group": "extraccion", "hint": "Incluir correos por regex sobre el texto (propenso a ruido; off por defecto)."},
            {"param_name": "field_selectors", "data_type": "json", "required": False, "group": "extraccion", "hint": "Para extract=fields: {campo: selector_css}."},
            {"param_name": "delay", "data_type": "float", "required": False, "default_value": 0.5, "group": "cortesia", "hint": "Segundos de pausa entre semillas."},
            {"param_name": "max_urls", "data_type": "integer", "required": False, "default_value": 0, "group": "fuente", "hint": "Límite de semillas a procesar. 0 = sin límite."},
        ],
    },
    {
        "name": "API REST",
        "class_path": "app.fetchers.rest.RestFetcher",
        "description": "APIs REST que devuelven JSON. Sin paginación hace una sola petición; eligiendo una estrategia de paginación (offset, número de página, enlace siguiente, cursor o bucle de pivotes) recorre el conjunto completo y acumula los registros.",
        "params": [
            {"param_name": "url", "data_type": "string", "required": True, "group": "http", "hint": "Dirección del endpoint. Ej.: https://api.ejemplo.es/v1/datos"},
            {"param_name": "method", "data_type": "string", "required": False, "default_value": "GET", "group": "http", "hint": "Verbo HTTP. Casi siempre GET; POST cuando la consulta viaja en el cuerpo."},
            {"param_name": "headers", "data_type": "json", "required": False, "group": "http", "hint": "Cabeceras HTTP en JSON. Ej.: {\"Accept\": \"application/json\", \"User-Agent\": \"OpenDataManager/1.0\"}"},
            {"param_name": "query_params", "data_type": "json", "required": False, "group": "http", "hint": "Parámetros fijos de la query string en JSON. Ej.: {\"formato\": \"json\", \"idioma\": \"ES\"}"},
            {"param_name": "timeout", "data_type": "integer", "required": False, "default_value": 30, "group": "http", "hint": "Segundos máximos de espera por respuesta. Típico 30-60; APIs lentas del sector público, 120-180."},
            {"param_name": "max_retries", "data_type": "integer", "required": False, "default_value": 3, "group": "http", "hint": "Reintentos ante fallo de red o 5xx, con espera creciente. Típico 3-5."},
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
                 {"value": "tree_flatten", "label": "Árbol aplanado", "help": "Respuestas jerárquicas (nodos con hijos): una fila por nodo con todos sus campos más nivel, padre y ruta."},
             ]},
            {"param_name": "children_field", "data_type": "string", "required": False, "default_value": "children", "group": "extraccion", "visible_when": {"param": "extraction", "in": ["tree_flatten"]},
             "hint": "Para extraction=tree_flatten: campo que contiene los hijos del nodo."},
            {"param_name": "label_field", "data_type": "string", "required": False, "default_value": "descripcion", "group": "extraccion", "visible_when": {"param": "extraction", "in": ["tree_flatten"]},
             "hint": "Para extraction=tree_flatten: campo descriptivo con el que se compone la ruta."},
            {"param_name": "const_fields", "data_type": "json", "required": False, "group": "extraccion",
             "hint": "Campos constantes de contexto que se añaden a cada registro, p. ej. {\"tipo_admon\": \"C\"}."},
            {"param_name": "field_map", "data_type": "json", "required": False, "group": "extraccion", "visible_when": {"param": "extraction", "in": ["field_map"]},
             "hint": "Para extraction=field_map: {campo_salida: ruta.con.puntos}."},
            {"param_name": "page_size", "data_type": "integer", "required": False, "group": "paginacion", "visible_when": {"param": "pagination", "in": ["query_offset", "page_number"]}, "hint": "Registros pedidos por página. Típico 50-1000 según lo que tolere el API."},
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
            {"param_name": "pivot_field_out", "data_type": "string", "required": False, "group": "paginacion", "visible_when": {"param": "pagination", "in": ["pivot_loop"]},
             "hint": "Si se indica, cada registro lleva el valor del pivote que lo produjo en este campo (útil cuando la respuesta no lo repite)."},
            {"param_name": "pivot_source_resource", "data_type": "string", "required": False, "group": "paginacion", "visible_when": {"param": "pagination", "in": ["pivot_loop"]},
             "hint": "Los valores del pivote salen de un dataset ya cosechado: NOMBRE del recurso fuente (preferido; la query se deriva sola)."},
            {"param_name": "pivot_source_odmgr_query", "data_type": "string", "required": False, "group": "paginacion", "visible_when": {"param": "pagination", "in": ["pivot_loop"]},
             "hint": "Alternativa avanzada: query GraphQL de datos directa del dataset fuente."},
            {"param_name": "pivot_source_field", "data_type": "string", "required": False, "group": "paginacion", "visible_when": {"param": "pagination", "in": ["pivot_loop"]},
             "hint": "Campo del dataset fuente cuyos valores se iteran (con pivot_source_odmgr_query)."},
            {"param_name": "pivot_source_filter_field", "data_type": "string", "required": False, "group": "paginacion", "visible_when": {"param": "pagination", "in": ["pivot_loop"]},
             "hint": "Filtro opcional sobre el dataset fuente: campo."},
            {"param_name": "pivot_source_filter_value", "data_type": "string", "required": False, "group": "paginacion", "visible_when": {"param": "pagination", "in": ["pivot_loop"]},
             "hint": "Filtro opcional sobre el dataset fuente: valor."},
            {"param_name": "query", "data_type": "string", "required": False, "group": "peticion",
             "hint": "Texto de la consulta; su lenguaje lo decide 'request' (GraphQL o SPARQL). Se valida la sintaxis al guardar el recurso.",
             "visible_when": {"param": "request", "in": ["graphql", "sparql"]}},
            {"param_name": "start_param", "data_type": "string", "required": False, "default_value": "start_index", "group": "paginacion", "visible_when": {"param": "pagination", "in": ["query_offset"]}, "hint": "Nombre del parámetro de desplazamiento en la query. Habituales: 'start', 'offset', '$offset', 'from'."},
            {"param_name": "page_size_param", "data_type": "string", "required": False, "default_value": "page_size", "group": "paginacion", "visible_when": {"param": "pagination", "in": ["query_offset", "page_number"]}, "hint": "Nombre del parámetro de tamaño de página. Habituales: 'rows', 'limit', '$limit', 'size', 'per_page'."},
            {"param_name": "delay", "data_type": "number", "required": False, "default_value": 0, "group": "http", "hint": "Cortesía: segundos de espera entre peticiones consecutivas. Habituales: 0 (APIs robustas), 1–2 (portales públicos)."},
            {"param_name": "id_field", "data_type": "string", "required": False, "group": "extraccion", "hint": "Campo identificador del registro, para deduplicar entre páginas o iteraciones. P. ej. 'id', '_about', 'identifier'. Vacío = sin deduplicación."}
        ],
    },
    {
        "name": "Feeds ATOM/RSS",
        "class_path": "app.fetchers.atom.AtomFetcher",
        "description": "ATOM/RSS feed reader",
        "params": [
            {"param_name": "url", "data_type": "string", "required": True, "group": "http", "hint": "Dirección del feed. Ej.: https://.../sindicacion/licitaciones.atom"},
            {"param_name": "max_items", "data_type": "integer", "required": False, "default_value": 1000, "group": "behavior", "hint": "Tope de entradas a cosechar (vacío = sin tope). Útil para acotar pruebas."},
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
{"param_name": "hasta", "data_type": "string", "required": False, "group": "incremental",
             "hint": "Techo temporal de la ventana (ISO). Vacío = sin techo: cosecha hasta lo más reciente.",
             "help_md": "Para feeds en orden descendente, la paginación se detiene al alcanzar entradas anteriores. 'auto' usa la marca de agua de la ejecución previa, evitando depender de max_pages."},
            {"param_name": "date_field", "data_type": "string", "required": False, "default_value": "fecha", "group": "incremental",
             "hint": "Campo de salida que contiene la fecha de la entrada (por defecto 'fecha')."},
            {"param_name": "timeout", "data_type": "integer", "required": False, "default_value": 30, "group": "http", "hint": "Segundos de espera máxima por petición. Habituales: 30; feeds pesados o ZIPs anuales: 120–180."},
            {"param_name": "max_pages", "data_type": "integer", "required": False, "default_value": 0, "group": "paginacion", "hint": "Tope de páginas a recorrer por ejecución (0 = sin tope). Útil en feeds con paginación profunda."},
            {"param_name": "dedup_key", "data_type": "string", "required": False, "group": "extraccion", "hint": "Campo por el que deduplicar el staging quedándose con la foto más reciente de cada entidad. P. ej. 'expediente'. Vacío = sin deduplicación."},
            {"param_name": "dedup_order_field", "data_type": "string", "required": False, "group": "extraccion", "hint": "Campo (fecha) que decide cuál es la foto más reciente al deduplicar por dedup_key. P. ej. 'fecha'."}
        ],
    },
    {
        "name": "Catálogo DCAT",
        "class_path": "app.fetchers.catalog.CatalogFetcher",
        "description": "Nave nodriza de catálogo: consulta un catálogo DCAT-AP-ES (por defecto datos.gob.es) y descubre un recurso-hijo por cada distribución descargable que pase la regla de selección. Cada candidato es autodescriptivo (especie-destino + url + formato), así que el hijo extrae con la especie que corresponda (típicamente File Download).",
        "params": [
            {"param_name": "catalog_api", "data_type": "string", "required": False, "default_value": "https://datos.gob.es/apidata", "group": "http", "hint": "Base de la apidata del catálogo DCAT-AP-ES. Por defecto el catálogo federado nacional datos.gob.es. En modo 'dcat-rdf' es la URL del feed RDF; en 'ckan' la base del portal CKAN."},
            {"param_name": "catalog_type", "data_type": "string", "required": False, "default_value": "datosgob", "enum_values": ["datosgob", "ckan", "dcat-rdf"], "group": "http", "hint": "Variante de catálogo: 'datosgob' (apidata JSON de datos.gob.es), 'ckan' (package_search de un portal CKAN) o 'dcat-rdf' (feed DCAT-AP servido como RDF/XML, Turtle o JSON-LD)."},
            {"param_name": "query_terms", "data_type": "string", "required": False, "default_value": "asociaciones,fundaciones", "group": "descubrimiento", "hint": "Palabras de título a consultar, separadas por coma. Una consulta por término."},
            {"param_name": "title_include", "data_type": "string", "required": False, "group": "descubrimiento", "hint": "Regex (ignora mayúsc.) que el título DEBE casar para considerarse pertinente. Vacío = patrón de registros por defecto."},
            {"param_name": "title_exclude", "data_type": "string", "required": False, "group": "descubrimiento", "hint": "Regex que descarta el dataset (ruido: pacientes, juveniles, estadísticas...). Vacío = patrón por defecto."},
            {"param_name": "formats", "data_type": "string", "required": False, "default_value": "csv,json", "group": "descubrimiento", "hint": "Formatos de distribución admitidos, separados por coma. Típico csv,json."},
            {"param_name": "drop_url_contains", "data_type": "string", "required": False, "default_value": "diccionario", "group": "descubrimiento", "hint": "Subcadenas que descartan una distribución (p. ej. los diccionarios de datos), separadas por coma."},
            {"param_name": "child_fetcher", "data_type": "string", "required": False, "default_value": "File Download", "group": "descubrimiento", "hint": "Especie-destino de los recursos-hijo. Normalmente 'File Download' para CSV/JSON directos."},
            {"param_name": "prefer_format", "data_type": "string", "required": False, "group": "descubrimiento", "hint": "Si un mismo registro se publica en varios formatos, quedarse solo con el preferido (lista por coma, p. ej. 'csv,json'). Conserva particiones (un fichero por provincia). Vacío = emitir todos los formatos."},
            {"param_name": "page_size", "data_type": "integer", "required": False, "default_value": 50, "group": "behavior", "hint": "Tamaño de página de la apidata. Típico 50."},
            {"param_name": "max_pages", "data_type": "integer", "required": False, "default_value": 20, "group": "behavior", "hint": "Límite de páginas por término. 20 × 50 = 1000 datasets por término."},
            {"param_name": "timeout", "data_type": "integer", "required": False, "default_value": 30, "group": "http", "hint": "Segundos máximos por consulta al catálogo."},
        ],
    },
    {
        "name": "Pivote",
        "class_path": "app.fetchers.pivot_discoverer.PivotDiscovererFetcher",
        "description": "Descubridor por pivote: lee los valores de un <select> de filtro (provincia, confesión...) en la página del formulario y emite un recurso-hijo por valor —o por GRUPO de valores (provincias→CCAA)—. Cada hijo es un searchloop que internaliza los valores de su grupo. Configúralo con los mismos params del searchloop hijo (url de acción, session_init_url de la página del form, search_field_name, extra_params, selectores, detail_level...) más la agrupación.",
        "params": [
            {"param_name": "search_field_name", "data_type": "string", "required": True, "group": "descubrimiento", "hint": "Nombre del <select> de filtro cuyas opciones son el pivote (p. ej. 'filtro.provincia')."},
            {"param_name": "pivot_group_map", "data_type": "string", "required": False, "group": "descubrimiento", "hint": "Agrupa los valores a un grano gobernable. Preset 'es_provincia_ccaa' (provincias INE→CCAA) o JSON {valor: grupo}. Vacío = un hijo por valor."},
            {"param_name": "pivot_form_url", "data_type": "string", "required": False, "group": "descubrimiento", "hint": "Página donde vive el <select> (si difiere de session_init_url). Por defecto session_init_url, y si no, url."},
            {"param_name": "child_fetcher", "data_type": "string", "required": False, "default_value": "HTML (genérico)", "group": "descubrimiento", "hint": "Especie-destino de los hijos. Normalmente 'HTML (genérico)' (navigation=searchloop)."},
            {"param_name": "url", "data_type": "string", "required": True, "group": "http", "hint": "Endpoint de ACCIÓN (POST de búsqueda) que heredan los hijos."},
            {"param_name": "session_init_url", "data_type": "string", "required": False, "group": "http", "hint": "Página del formulario: abre sesión y contiene el <select> a descubrir."},
        ],
    },
    {
        "name": "Descubridor REST",
        "class_path": "app.fetchers.rest_api_discoverer.RestApiDiscovererFetcher",
        "description": "Descubridor de API REST: lee el OpenAPI de una API y emite un hijo 'API REST' por cada dataset (patrón /{nombre}/busqueda, paginado) y, opcionalmente, por cada catálogo lookup. Por defecto apunta a SNPSAP/BDNS. Los hijos usan 'busqueda' (JSON estructurado, filtrable por nifCif/fecha), no 'exportar' — verificado que son proyecciones distintas. Quinta estrategia de descubrimiento. Solo modo descubrir.",
        "params": [
            {"param_name": "openapi_url", "data_type": "string", "required": False, "group": "descubrimiento", "hint": "URL del OpenAPI/Swagger a leer. Por defecto el de SNPSAP/BDNS (estaticos/doc/snpsap-api.json)."},
            {"param_name": "api_base", "data_type": "string", "required": False, "group": "descubrimiento", "hint": "Base de la API REST que heredan los hijos. Por defecto https://www.infosubvenciones.es/bdnstrans/api"},
            {"param_name": "vpd", "data_type": "string", "required": False, "default_value": "GE", "group": "descubrimiento", "hint": "Portal virtual (obligatorio en BDNS). GE = estado general; o el código del portal de cada CCAA."},
            {"param_name": "page_size", "data_type": "integer", "required": False, "default_value": 100, "group": "descubrimiento", "hint": "Tamaño de página que se preconfigura en los hijos paginados."},
            {"param_name": "include_lookups", "data_type": "string", "required": False, "group": "descubrimiento", "hint": "'true' para emitir también los catálogos lookup (regiones, objetivos, órganos...) como hijos pequeños. Vacío = solo los datasets."},
            {"param_name": "child_fetcher", "data_type": "string", "required": False, "default_value": "API REST", "group": "descubrimiento", "hint": "Especie-destino de los hijos. Normalmente 'API REST'."},
        ],
    },
    {
        "name": "File Download",
        "class_path": "app.fetchers.file_download.FileDownloadFetcher",
        "description": "Downloads a static file and converts rows to records. Supports PDF, XLS, XLSX, CSV and TSV.",
        "params": [
            {"param_name": "url", "data_type": "string", "required": True, "group": "http", "hint": "Dirección del fichero a descargar. Ej.: https://portal.es/datos/listado.xlsx"},
            {"param_name": "format", "data_type": "string", "required": True, "group": "format", "hint": "Formato del fichero: csv, xlsx, xls, json o html. Si se omite se infiere de la URL."},
            {"param_name": "sheet", "data_type": "string", "required": False, "default_value": "0", "group": "excel", "hint": "Hoja del libro Excel a leer, por nombre o índice (0 = primera)."},
            {"param_name": "skip_rows", "data_type": "integer", "required": False, "default_value": 0, "group": "tabular", "hint": "Filas a saltar antes de la cabecera (títulos, notas...). Típico 0-5."},
            {"param_name": "delimiter", "data_type": "string", "required": False, "group": "tabular", "hint": "Separador del CSV. Típico ',' o ';' (frecuente en ficheros españoles)."},
            {"param_name": "encoding", "data_type": "string", "required": False, "default_value": "utf-8-sig", "group": "tabular", "hint": "Codificación del fichero. Típico utf-8; ficheros antiguos de la administración, latin-1 o cp1252."},
            {"param_name": "columns", "data_type": "json", "required": False, "group": "tabular", "hint": "Lista JSON de columnas a conservar (vacío = todas). Ej.: [\"nombre\", \"provincia\"]"},
            {"param_name": "headers", "data_type": "json", "required": False, "group": "http", "hint": "Cabeceras HTTP de la descarga en JSON (User-Agent, cookies...)."},
            {"param_name": "batch_size", "data_type": "integer", "required": False, "default_value": 1000, "group": "behavior", "hint": "Filas por lote al volcar a staging. Típico 500-5000."},
            {"param_name": "timeout", "data_type": "integer", "required": False, "default_value": 60, "group": "http", "hint": "Segundos máximos de descarga. Ficheros grandes: 120-300."},
            {"param_name": "table_index", "data_type": "integer", "required": False, "default_value": 0, "group": "pdf", "hint": "Si el fichero es HTML: cuál de sus tablas leer (0 = primera)."},
            {"param_name": "header_row", "data_type": "integer", "required": False, "default_value": 0, "group": "pdf", "hint": "Fila que contiene los nombres de columna (0 = primera tras skip_rows)."},
            {"param_name": "custom_parser", "data_type": "string", "required": False, "group": "specialization", "hint": "Parser a medida como 'modulo.funcion' para ficheros que no siguen ningún formato estándar."},
        ],
    },
    {
        "name": "Compressed File",
        "class_path": "app.fetchers.compressed_file.CompressedFileFetcher",
        "description": "Archivo comprimido (ZIP/TAR/TAR.GZ/TAR.BZ2/GZ). Modos: extraer (saca una entrada y la parsea como PDF/XLS/XLSX/CSV/TSV/JSON) y descubrir (Archivo como Colección: lista los miembros de datos y emite un hijo por fichero, cada uno autodescriptivo con su entry e inner_format).",
        "params": [
            {"param_name": "url", "data_type": "string", "required": True, "group": "http", "hint": "Dirección del archivo comprimido (zip, gz, tar...)."},
            {"param_name": "format", "data_type": "string", "required": True, "group": "archive", "hint": "Formato del contenedor: zip, gz, tar... Si se omite se infiere de la URL."},
            {"param_name": "entry", "data_type": "string", "required": False, "group": "archive", "hint": "Nombre o patrón del fichero a extraer del archivo (vacío = el primero compatible). Ej.: *.csv"},
            {"param_name": "inner_format", "data_type": "string", "required": False, "group": "format", "hint": "Formato del fichero interior: csv, xlsx, json, xml..."},
            {"param_name": "skip_rows", "data_type": "integer", "required": False, "default_value": 0, "group": "tabular", "hint": "Filas a saltar antes de la cabecera del fichero interior."},
            {"param_name": "delimiter", "data_type": "string", "required": False, "group": "tabular", "hint": "Separador si el interior es CSV. Típico ',' o ';'."},
            {"param_name": "encoding", "data_type": "string", "required": False, "default_value": "utf-8-sig", "group": "tabular", "hint": "Codificación del fichero interior. Típico utf-8 o latin-1."},
            {"param_name": "sheet", "data_type": "string", "required": False, "default_value": "0", "group": "excel", "hint": "Hoja a leer si el interior es un libro Excel (nombre o índice)."},
            {"param_name": "columns", "data_type": "json", "required": False, "group": "tabular", "hint": "Lista JSON de columnas a conservar (vacío = todas)."},
            {"param_name": "headers", "data_type": "json", "required": False, "group": "http", "hint": "Cabeceras HTTP de la descarga en JSON."},
            {"param_name": "batch_size", "data_type": "integer", "required": False, "default_value": 1000, "group": "behavior", "hint": "Filas por lote al volcar a staging. Típico 500-5000."},
            {"param_name": "timeout", "data_type": "integer", "required": False, "default_value": 120, "group": "http", "hint": "Segundos máximos de descarga. Archivos anuales grandes: 300+."},
            {"param_name": "table_index", "data_type": "integer", "required": False, "default_value": 0, "group": "pdf", "hint": "Si el interior es HTML: cuál de sus tablas leer (0 = primera)."},
            {"param_name": "header_row", "data_type": "integer", "required": False, "default_value": 0, "group": "pdf", "hint": "Fila con los nombres de columna del fichero interior."},
            {"param_name": "custom_parser", "data_type": "string", "required": False, "group": "specialization", "hint": "Parser a medida como 'modulo.funcion' para interiores no estándar."},
        ],
    },
    {
        "name": "Power BI",
        "class_path": "app.fetchers.powerbi.PowerBIFetcher",
        "description": "Extrae datos de reports públicos de Power BI (los paneles embebidos que publican muchos organismos). Lee cualquier visual del report usando la API pública de querydata, con paginación automática por restart tokens y decodificación del formato DSR. Necesita los identificadores del report embebido (resource_key, model_id, dataset_id, report_id, visual_id) y la consulta semántica (query_json). Caso de uso documentado: Registro de Entidades Religiosas (config_rer.md).",
        "params": [
            {"param_name": "resource_key", "data_type": "string", "required": True, "group": "http",
             "hint": "X-PowerBI-ResourceKey: campo 'k' del token del embed público."},
            {"param_name": "model_id", "data_type": "integer", "required": True, "group": "peticion", "hint": "Identificador del modelo del informe Power BI público (se ve en las peticiones querydata del navegador)."},
            {"param_name": "dataset_id", "data_type": "string", "required": True, "group": "peticion", "hint": "Identificador del dataset dentro del informe (cabecera X-PowerBI-ResourceKey o cuerpo de querydata)."},
            {"param_name": "report_id", "data_type": "string", "required": True, "group": "peticion", "hint": "Identificador del informe publicado (en la URL de embed)."},
            {"param_name": "visual_id", "data_type": "string", "required": False, "default_value": "powerbi_fetcher", "group": "peticion",
             "hint": "Cualquier ID de visual válido del report; la clase usa un valor por defecto si no se indica."},
            {"param_name": "query_json", "data_type": "json", "required": True, "group": "peticion",
             "hint": "SemanticQuery completa: {From:[...], Select:[...], Where:[...], OrderBy:[...]}."},
            {"param_name": "projections", "data_type": "string", "required": False, "group": "extraccion",
             "hint": "Índices de proyección separados por coma, p. ej. '0,1,2'."},
            {"param_name": "field_mapping", "data_type": "json", "required": False, "group": "extraccion",
             "hint": "Mapa Gn → nombre de campo, p. ej. {\"G0\": \"nombre\", \"G1\": \"web\"}. Sin definir: G0, G1, ..."},
            {"param_name": "page_size", "data_type": "integer", "required": False, "default_value": 500, "group": "paginacion", "hint": "Filas por consulta al motor. Típico 500-30000 según el visual."},
            {"param_name": "delay", "data_type": "number", "required": False, "default_value": 0.3, "group": "behavior", "hint": "Segundos de cortesía entre consultas. Típico 1-3."},
            {"param_name": "timeout", "data_type": "integer", "required": False, "default_value": 60, "group": "http", "hint": "Segundos máximos por consulta. Típico 60-120."},
        ],
    },
    {
        "name": "HTML (genérico)",
        "class_path": "app.fetchers.html_generic.HTMLFetcher",
        "description": "Scraping de páginas HTML. La navegación (página única, paginada, por pivotes o rellenando formularios) y la extracción (campos por selectores o tablas) se eligen por parámetros.",
        "params": [
            {"param_name": "url", "data_type": "string", "required": False, "group": "http", "hint": "Dirección de la página (o plantilla con {pivot} si se navega por pivotes)."},
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
            {"param_name": "field_selectors", "data_type": "json", "required": False, "group": "extraccion", "visible_when": {"param": "extraction", "in": ["fields"]}, "hint": "Mapa JSON campo→selector CSS cuyo texto se extrae. Ej.: {\"titulo\": \"h2 a\"}"},
            {"param_name": "field_attr_selectors", "data_type": "json", "required": False, "group": "extraccion", "visible_when": {"param": "extraction", "in": ["fields"]}, "hint": "Mapa JSON campo→[selector, atributo] para extraer atributos. Ej.: {\"enlace\": [\"h2 a\", \"href\"]}"},
            {"param_name": "field_all_selectors", "data_type": "json", "required": False, "group": "extraccion", "visible_when": {"param": "extraction", "in": ["fields"]}, "hint": "Como field_selectors pero recogiendo TODAS las coincidencias en lista."},
            {"param_name": "field_all_text", "data_type": "json", "required": False, "group": "extraccion", "visible_when": {"param": "extraction", "in": ["fields"]}, "hint": "Campos cuyo valor es todo el texto de la fila/elemento, separados por coma."},
            {"param_name": "field_attrs", "data_type": "json", "required": False, "group": "extraccion", "visible_when": {"param": "extraction", "in": ["fields"]}, "hint": "Mapa JSON campo→atributo a leer del propio elemento fila."},
            {"param_name": "field_label_selectors", "data_type": "json", "required": False, "group": "extraccion", "visible_when": {"param": "extraction", "in": ["fields"]}, "hint": "Mapa JSON campo→etiqueta visible (pares etiqueta/valor en fichas)."},
            {"param_name": "next_page_selector", "data_type": "string", "required": False, "group": "navegacion", "visible_when": {"param": "navigation", "in": ["paged", "pivot"]}, "hint": "Selector CSS del enlace 'siguiente' para la navegación paginada."},
            {"param_name": "next_page_attr", "data_type": "string", "required": False, "default_value": "href", "group": "navegacion", "visible_when": {"param": "navigation", "in": ["paged", "pivot"]}, "hint": "Atributo del enlace siguiente con la URL. Típico href."},
            {"param_name": "pivot_values", "data_type": "json", "required": False, "group": "navegacion", "visible_when": {"param": "navigation", "in": ["pivot", "form_pivot"]}, "hint": "Lista JSON de valores a iterar en la URL ({pivot}). Ej.: códigos de provincia."},
            {"param_name": "search_field_values", "data_type": "json", "required": False, "group": "navegacion", "visible_when": {"param": "navigation", "in": ["pivot", "form_pivot"]}, "hint": "Lista JSON de valores a enviar en el campo del formulario, uno por búsqueda."},
            {"param_name": "search_field_name", "data_type": "string", "required": False, "group": "navegacion", "visible_when": {"param": "navigation", "in": ["form_pivot"]}, "hint": "Atributo name del campo del formulario que se rellena en cada búsqueda."},
            {"param_name": "form_selector", "data_type": "string", "required": False, "group": "navegacion", "visible_when": {"param": "navigation", "in": ["form_pivot"]}, "hint": "Selector CSS del formulario a enviar (vacío = el primero de la página)."},
            {"param_name": "next_form_selector", "data_type": "string", "required": False, "group": "navegacion",
             "hint": "Selector(es) CSS del formulario de paginación (admite lista separada por comas).",
             "visible_when": {"param": "navigation", "in": ["form_paged"]}},
            {"param_name": "page_param", "data_type": "string", "required": False, "default_value": "pagina", "group": "navegacion",
             "visible_when": {"param": "navigation", "in": ["form_paged"]},
             "hint": "Nombre del parámetro de página en la URL cuando la navegación es paginada. Habituales: 'page', 'p', 'pagina'."},
            {"param_name": "pivot_source_odmgr_query", "data_type": "string", "required": False, "group": "navegacion", "visible_when": {"param": "navigation", "in": ["pivot"]}, "hint": "Alternativa avanzada: query GraphQL de datos del dataset del que tomar los pivotes."},
            {"param_name": "pivot_source_field", "data_type": "string", "required": False, "group": "navegacion", "visible_when": {"param": "navigation", "in": ["pivot"]}, "hint": "Campo del dataset fuente cuyos valores se iteran como pivotes."},
            {"param_name": "max_pages", "data_type": "integer", "required": False, "default_value": 500, "group": "navegacion", "visible_when": {"param": "navigation", "in": ["paged", "pivot"]}, "hint": "Tope de páginas a recorrer (vacío = hasta que no haya siguiente)."},
            {"param_name": "start_page", "data_type": "integer", "required": False, "default_value": 1, "group": "navegacion", "visible_when": {"param": "navigation", "in": ["paged", "pivot"]}, "hint": "Número de la primera página. Típico 1; algunos portales empiezan en 0."},
            {"param_name": "delay_between_pages", "data_type": "number", "required": False, "default_value": 1.0, "group": "behavior", "hint": "Segundos de cortesía entre páginas. Típico 1-3."},
            {"param_name": "headers", "data_type": "json", "required": False, "group": "http", "hint": "Cabeceras HTTP en JSON (User-Agent realista, cookies...)."},
            {"param_name": "timeout", "data_type": "integer", "required": False, "default_value": 30, "group": "http", "hint": "Segundos máximos por petición. Típico 30-60."},
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
            {"param_name": "query", "data_type": "overpass_query", "required": True, "group": "query", "hint": "Consulta Overpass QL construida con el asistente; define qué elementos del mapa se extraen."},
            {"param_name": "timeout", "data_type": "integer", "required": False, "default_value": 120, "group": "http", "hint": "Segundos máximos de la consulta en el servidor Overpass. Consultas amplias: 120-300."},
        ],
    },
    {
        "name": "WFS",
        "class_path": "app.fetchers.wfs.WFSFetcher",
        "description": "OGC Web Feature Service — vector features with automatic pagination",
        "params": [
            {"param_name": "endpoint", "data_type": "string", "required": True, "group": "request", "hint": "URL base del servicio WFS. Ej.: https://www.ign.es/wfs/redes-geodesicas"},
            {"param_name": "typenames", "data_type": "string", "required": True, "group": "request", "hint": "Capa(s) a descargar, separadas por coma. Se listan con GetCapabilities."},
            {"param_name": "version", "data_type": "string", "required": False, "default_value": "2.0.0", "group": "request", "hint": "Versión del protocolo. Típico 2.0.0; servicios antiguos, 1.1.0."},
            {"param_name": "outputFormat", "data_type": "string", "required": False, "default_value": "application/json", "group": "request", "hint": "Formato de salida. Típico application/json (GeoJSON) o GML."},
            {"param_name": "srsName", "data_type": "string", "required": False, "default_value": "EPSG:4326", "group": "request", "hint": "Sistema de referencia de las geometrías. Típico EPSG:4326 o EPSG:25830 (península)."},
            {"param_name": "bbox", "data_type": "bbox", "required": False, "group": "filter", "hint": "Recorte espacial minx,miny,maxx,maxy en el SRS elegido (vacío = todo el ámbito)."},
            {"param_name": "cql_filter", "data_type": "string", "required": False, "group": "filter", "hint": "Filtro CQL sobre atributos. Ej.: provincia='Sevilla'"},
            {"param_name": "count", "data_type": "integer", "required": False, "default_value": 1000, "group": "pagination", "hint": "Entidades por página de descarga. Típico 1000-5000."},
            {"param_name": "id_field", "data_type": "string", "required": False, "group": "behavior", "hint": "Campo identificador para deduplicar entre páginas."},
            {"param_name": "timeout", "data_type": "integer", "required": False, "default_value": 120, "group": "http", "hint": "Segundos máximos por petición. Típico 60-180."},
        ],
    },
    {
        "name": "WMS",
        "class_path": "app.fetchers.wms.WMSFetcher",
        "description": "OGC Web Map Service — map image metadata + URL",
        "params": [
            {"param_name": "endpoint", "data_type": "string", "required": True, "group": "request", "hint": "URL base del servicio WMS."},
            {"param_name": "layers", "data_type": "string", "required": True, "group": "request", "hint": "Capa(s) a pedir en el GetMap, separadas por coma."},
            {"param_name": "bbox", "data_type": "bbox", "required": True, "group": "request", "hint": "Extensión de la imagen minx,miny,maxx,maxy en el CRS elegido."},
            {"param_name": "version", "data_type": "string", "required": False, "default_value": "1.3.0", "group": "request", "hint": "Versión del protocolo. Típico 1.3.0."},
            {"param_name": "format", "data_type": "string", "required": False, "default_value": "image/png", "group": "request", "hint": "Formato de imagen. Típico image/png o image/jpeg."},
            {"param_name": "crs", "data_type": "string", "required": False, "default_value": "EPSG:4326", "group": "request", "hint": "Sistema de referencia. Típico EPSG:4326 o EPSG:25830."},
            {"param_name": "styles", "data_type": "string", "required": False, "group": "request", "hint": "Estilo de representación (vacío = el por defecto del servidor)."},
            {"param_name": "width", "data_type": "integer", "required": False, "default_value": 1024, "group": "request", "hint": "Ancho de la imagen en píxeles. Típico 1024-4096."},
            {"param_name": "height", "data_type": "integer", "required": False, "default_value": 1024, "group": "request", "hint": "Alto de la imagen en píxeles. Típico 1024-4096."},
            {"param_name": "timeout", "data_type": "integer", "required": False, "default_value": 120, "group": "http", "hint": "Segundos máximos por petición. Típico 60-120."},
        ],
    },
    {
        "name": "Servicios SOAP/WSDL",
        "class_path": "app.fetchers.soap.SoapFetcher",
        "description": "SOAP/WSDL web service",
        "params": [
            {"param_name": "wsdl", "data_type": "string", "required": True, "group": "request", "hint": "URL del contrato WSDL del servicio. Ej.: https://servicio.es/ws?wsdl"},
            {"param_name": "operation", "data_type": "string", "required": True, "group": "request", "hint": "Operación del servicio a invocar, tal como aparece en el WSDL."},
        ],
    },
    {
        "name": "XBRL ZIP",
        "class_path": "app.fetchers.xbrl.XbrlFetcher",
        "description": "Generic fetcher for ZIP archives containing XBRL documents.",
        "params": [
            {"param_name": "url", "data_type": "string", "required": True, "group": "http", "hint": "Dirección del ZIP con los ficheros XBRL (cuentas anuales, presupuestos...)."},
            {"param_name": "method", "data_type": "string", "required": False, "default_value": "GET", "group": "http", "hint": "Verbo HTTP de la descarga. Casi siempre GET."},
            {"param_name": "query_params", "data_type": "json", "required": False, "group": "http", "hint": "Parámetros de la query string en JSON (ejercicio, entidad...)."},
            {"param_name": "headers", "data_type": "json", "required": False, "group": "http", "hint": "Cabeceras HTTP de la descarga en JSON."},
            {"param_name": "timeout", "data_type": "integer", "required": False, "default_value": 120, "group": "http", "hint": "Segundos máximos de descarga. Típico 120-300."},
            {"param_name": "xml_pattern", "data_type": "string", "required": False, "group": "zip", "hint": "Patrón de los XML a procesar dentro del ZIP. Ej.: *.xbrl"},
            {"param_name": "entry", "data_type": "string", "required": False, "group": "zip", "hint": "Nombre o patrón de una entrada concreta del ZIP (vacío = todas las que casen con xml_pattern)."},
            {"param_name": "file_classifier", "data_type": "json", "required": False, "group": "zip", "hint": "Mapa JSON palabra_clave→etiqueta para clasificar cada fichero por su nombre. Ej.: {\"PEN\": \"penal\"}"},
            {"param_name": "context_fields", "data_type": "json", "required": False, "group": "output", "hint": "Mapa JSON campo→valor fijo añadido a cada registro. Ej.: {\"ejercicio\": \"2023\"}"},
            {"param_name": "account_prefix", "data_type": "string", "required": False, "group": "output", "hint": "Prefijo(s) de tag contable a incluir, separados por coma (vacío = todos)."},
            {"param_name": "exclude_tags", "data_type": "string", "required": False, "group": "output", "hint": "Tags de infraestructura XBRL a ignorar, separados por coma (context, unit, schemaRef...)."},
            {"param_name": "batch_size", "data_type": "integer", "required": False, "default_value": 200, "group": "output", "hint": "Registros por lote al volcar a staging."},
        ],
    },
    {
        "name": "PDF_TABLE",
        "class_path": "app.fetchers.pdf_table.PdfTableFetcher",
        "description": "Fetcher for PDFs: iterates a year/month/quarter date range and extracts tables with pdfplumber.",
        "params": [
            {"param_name": "url_template", "data_type": "string", "required": True, "group": "url", "hint": "URL con huecos {year}, {month} o {quarter} que se rellenan en cada iteración. Ej.: https://web.es/informes/{year}/{month}.pdf"},
            {"param_name": "granularity", "data_type": "string", "required": True, "group": "date_range", "hint": "Cadencia de los ficheros: monthly, quarterly o annual; decide qué huecos se iteran."},
            {"param_name": "year_from", "data_type": "integer", "required": True, "group": "date_range", "hint": "Primer año a recorrer. Ej.: 2018"},
            {"param_name": "year_to", "data_type": "integer", "required": True, "group": "date_range", "hint": "Último año a recorrer (vacío = el actual)."},
            {"param_name": "table_index", "data_type": "integer", "required": False, "default_value": 0, "group": "extraction", "hint": "Cuál de las tablas del PDF leer (0 = primera)."},
            {"param_name": "header_row", "data_type": "integer", "required": False, "default_value": 0, "group": "extraction", "hint": "Fila de la tabla con los nombres de columna (0 = primera)."},
            {"param_name": "batch_size", "data_type": "integer", "required": False, "default_value": 500, "group": "behavior", "hint": "Filas por lote al volcar a staging."},
            {"param_name": "timeout", "data_type": "integer", "required": False, "default_value": 60, "group": "http", "hint": "Segundos máximos por descarga de PDF."},
        ],
    },
    {
        "name": "Web Tree",
        "class_path": "app.fetchers.web_tree_fetcher.WebTreeFetcher",
        "description": "Crawler de portales web clásicos. En modo discover (Resource padre, parent_resource_id=NULL) recorre el árbol e infiere agrupaciones por dimensiones (year, month, quarter, ...) que el operador revisa y promueve. En modo stream (Resource hijo promovido) descarga las URLs de su ResourceCandidate enriqueciendo cada registro con las dimensiones detectadas.",
        "params": [
            {"param_name": "extract_mode", "data_type": "string", "required": False, "group": "output",
             "hint": "Qué produce cada fichero: 'datos' lo descarga y parsea a filas (tablas); 'censo' emite una fila por fichero con dimensiones+url+formato, sin descargar; 'receta' aplica capturas declarativas (param receta) y emite una fila limpia por fichero."},
            {"param_name": "receta", "data_type": "json", "required": False, "group": "output",
             "hint": "Capturas para extract_mode=receta. Lista de {campo, etiqueta(regex), tipo: numero|texto, posicion?: celda|derecha|debajo}. P. ej. [{\"campo\": \"pmp_global_dias\", \"etiqueta\": \"Periodo Medio de Pago Global\", \"tipo\": \"numero\"}]."},
            {"param_name": "root_url", "data_type": "string", "required": True, "group": "navigation",
             "hint": "URL raíz desde la que arranca el recorrido. P. ej. https://transparencia.<municipio>.es/economica/deuda."},
            {"param_name": "path_prefix", "data_type": "string", "required": False, "group": "navigation",
             "hint": "Acota la navegación a esta subrama del path (las páginas fuera no se siguen). Vacío = la carpeta del root_url. P. ej. /infopublica/economica/deuda."},
            {"param_name": "include_patterns", "data_type": "json", "required": False, "group": "navigation",
             "hint": "Lista de expresiones regulares: una hoja se conserva solo si alguna casa con su URL. Vacío = todas. P. ej. [\"/a07-economica/c-deuda/\"]."},
            {"param_name": "exclude_patterns", "data_type": "json", "required": False, "group": "navigation",
             "hint": "Lista de expresiones regulares: descarta páginas y hojas cuya URL case con alguna. P. ej. [\"/archivo/\", \"borrador\"]."},
        ],
    },
]

# ── Catálogo de tecnologías de entrega (especies). Descripción larga con
# explicación y casos de uso. Marcadas como planificadas hasta implementar su clase.
FETCHERS += [{'name': 'GraphQL',
  'class_path': 'app.fetchers.graphql.GraphQLFetcher',
  'description': 'Consulta declarativa sobre un único '
                 'endpoint: el cliente pide en el cuerpo exactamente los campos que necesita; paginación por '
                 'cursor/connections. Casos de uso: GitHub y Shopify lo popularizaron; en sector público es '
                 'emergente — algunos catálogos y portales de transparencia lo exponen junto a REST; data.europa.eu '
                 'experimenta con endpoints GraphQL.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http', 'hint': 'Endpoint GraphQL del servicio (único para todas las consultas). P. ej. https://<servicio>/graphql.'}]},
 {'name': 'SPARQL',
  'class_path': 'app.fetchers.sparql.SparqlFetcher',
  'description': 'Consulta sobre datos enlazados '
                 '(RDF); los resultados llegan en results.bindings (JSON/XML). Casos de uso: endpoint SPARQL del '
                 'catálogo de datos.gob.es; Aragón Open Data (Linked Data); datos enlazados del BOE (legislación); '
                 'Wikidata, Europeana y el Cellar/EU Vocabularies de la Oficina de Publicaciones de la UE.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http', 'hint': 'Endpoint SPARQL del triplestore. P. ej. https://datos.gob.es/virtuoso/sparql o https://<portal>/sparql.'}]},
 {'name': 'SDMX',
  'class_path': 'app.fetchers.sdmx.SdmxFetcher',
  'description': 'Estándar de intercambio de datos y '
                 'metadatos ESTADÍSTICOS: dataflows, dimensiones y atributos en SDMX-JSON/XML. Casos de uso: INE '
                 '(API Tempus3/SDMX), Eurostat, Banco de España, Banco Central Europeo, OCDE, FMI y Banco Mundial.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http', 'hint': 'URL base del API SDMX del organismo estadístico. P. ej. https://sdmx.ine.es/rest o el de Eurostat.'}]},
 {'name': 'OAI-PMH',
  'class_path': 'app.fetchers.oai_pmh.OaiPmhFetcher',
  'description': 'Protocolo de cosecha de metadatos de '
                 "repositorios: verbos ListRecords/ListIdentifiers encadenados por 'resumption token'. Casos de uso: "
                 'Hispana y Europeana (agregación cultural), repositorios universitarios y del CSIC (DSpace), '
                 'TESEO/tesis, Biblioteca Nacional, DataCite y OpenAIRE.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http', 'hint': 'URL base del repositorio OAI-PMH (sin el ?verb=...). P. ej. https://<repositorio>/oai/request.'}]},
 {'name': 'OGC API - Features',
  'class_path': 'app.fetchers.ogc_features.OgcFeaturesFetcher',
  'description': 'Sucesor en JSON/GeoJSON de WFS: '
                 "colecciones de entidades geográficas paginadas por enlaces 'next'. Casos de uso: IGN/CNIG y la "
                 'IDEE, Dirección General del Catastro, IDEs autonómicas (ICGC de Cataluña, IDEAndalucía, '
                 'geoEuskadi) y geoportales de data.europa.eu.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http', 'hint': 'Raíz del servicio OGC API Features. P. ej. https://<ide>/ogcapi (las colecciones cuelgan de /collections).'}]},
 {'name': 'CSW',
  'class_path': 'app.fetchers.csw.CswFetcher',
  'description': 'Catalogue Service for the Web (OGC): '
                 'catálogo de metadatos geográficos ISO 19139 para descubrir capas y datasets. Casos de uso: '
                 'catálogos INSPIRE del IGN y la IDEE, catálogos de las IDEs autonómicas y municipales, geoportales '
                 'europeos.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http', 'hint': 'Endpoint CSW del catálogo de metadatos. P. ej. https://<ide>/csw (admite GetRecords).'}]},
 {'name': 'WMTS',
  'class_path': 'app.fetchers.wmts.WmtsFetcher',
  'description': 'Teselas de mapa precalculadas (OGC '
                 'Web Map Tile Service). Casos de uso: PNOA y ortofotos del IGN, cartografía base de IDEs '
                 'autonómicas y de muchos ayuntamientos.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http', 'hint': 'URL del GetCapabilities del servicio de teselas. P. ej. https://<ide>/wmts?request=GetCapabilities.'}]},
 {'name': 'WCS',
  'class_path': 'app.fetchers.wcs.WcsFetcher',
  'description': 'Coberturas ráster (OGC Web Coverage '
                 'Service): datos continuos como elevación o temperatura. Casos de uso: modelos digitales del '
                 'terreno del IGN, mallas climáticas de AEMET y de Copernicus.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http', 'hint': 'Endpoint WCS del servicio de coberturas. P. ej. https://<ide>/wcs.'}]},
 {'name': 'STAC',
  'class_path': 'app.fetchers.stac.StacFetcher',
  'description': 'SpatioTemporal Asset Catalog: '
                 'catálogo de activos geoespacial-temporales (imágenes de satélite y ortofotos). Casos de uso: '
                 'Copernicus Data Space (Sentinel), PNOA histórico del IGN, y catálogos internacionales (USGS, '
                 'Microsoft Planetary Computer, AWS Open Data).',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http', 'hint': 'Raíz del catálogo STAC. P. ej. https://<servicio>/stac (de ahí cuelgan collections y search).'}]},
 {'name': 'ArcGIS REST',
  'class_path': 'app.fetchers.arcgis.ArcGisFetcher',
  'description': 'API REST de ArcGIS '
                 '(FeatureServer/MapServer): query?f=json con paginación por resultOffset/resultRecordCount. Casos '
                 'de uso: ubicua en GIS público — visores urbanísticos, callejeros y equipamientos de numerosos '
                 'ayuntamientos y CCAA, y organismos estatales con infraestructura Esri.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http', 'hint': 'URL de la capa FeatureServer/MapServer, terminada en el índice de capa. P. ej. https://<servidor>/arcgis/rest/services/<svc>/FeatureServer/0.'}]},
 {'name': 'NGSI-LD (FIWARE)',
  'class_path': 'app.fetchers.ngsi_ld.NgsiLdFetcher',
  'description': 'Datos de contexto en (casi) tiempo '
                 'real en JSON-LD a través de un Context Broker (FIWARE). Casos de uso: ciudades inteligentes '
                 'españolas sobre FIWARE — Santander, Málaga, Valencia, Sevilla — y la Red Española de Ciudades '
                 'Inteligentes (RECI).',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http', 'hint': 'URL del Context Broker. P. ej. https://<broker>:1026/ngsi-ld/v1.'}]},
 {'name': 'Server-Sent Events',
  'class_path': 'app.fetchers.sse.SseFetcher',
  'description': 'Flujo unidireccional '
                 'servidor→cliente sobre HTTP (text/event-stream). Casos de uso: paneles y alertas en vivo, APIs de '
                 'tráfico y movilidad en tiempo real.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http', 'hint': 'URL del flujo de eventos (Content-Type text/event-stream).'}]},
 {'name': 'WebSocket',
  'class_path': 'app.fetchers.websocket.WebSocketFetcher',
  'description': 'Canal bidireccional persistente para '
                 'datos en vivo. Casos de uso: posiciones de transporte, mercados, telemetría de sensores.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http', 'hint': 'URL del socket, esquema ws:// o wss://. P. ej. wss://<servicio>/stream.'}]},
 {'name': 'MQTT',
  'class_path': 'app.fetchers.mqtt.MqttFetcher',
  'description': 'Pub/sub ligero orientado a IoT '
                 '(suscripción a topics de un broker). Casos de uso: sensórica de ciudades inteligentes y medio '
                 'ambiente (calidad del aire, aforo, ruido), habitual en plataformas FIWARE.',
  'params': [{'param_name': 'broker', 'data_type': 'string', 'required': True, 'group': 'http', 'hint': 'Host del broker MQTT, con puerto si no es el estándar. P. ej. mqtt.<organismo>.es:1883 (TLS habitual: 8883).'}]},
 {'name': 'Apache Kafka',
  'class_path': 'app.fetchers.kafka.KafkaFetcher',
  'description': 'Bus de eventos de alto volumen '
                 '(consumo de topics). Casos de uso: integración interna de grandes administraciones y plataformas '
                 'de datos en tiempo real.',
  'params': [{'param_name': 'brokers', 'data_type': 'string', 'required': True, 'group': 'http', 'hint': 'Lista de brokers separados por comas (bootstrap servers). P. ej. kafka1:9092,kafka2:9092.'}]},
 {'name': 'GTFS-RT',
  'class_path': 'app.fetchers.gtfs_rt.GtfsRtFetcher',
  'description': 'Transporte público en tiempo real '
                 '(posiciones, retrasos, incidencias) en protobuf sobre HTTP. Casos de uso: EMT Madrid, TMB '
                 'Barcelona y consorcios de transporte autonómicos; estándar internacional mantenido por '
                 'MobilityData/Google.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http', 'hint': 'URL del feed GTFS-Realtime en protobuf. P. ej. https://<operador>/gtfs-rt/vehicle-positions.'}]},
 {'name': 'Webhooks entrantes',
  'class_path': 'app.fetchers.webhook_in.WebhookInFetcher',
  'description': 'La fuente EMPUJA eventos a un '
                 'endpoint que tú expones (push, no pull). Casos de uso: notificaciones de cambios de catálogo y de '
                 'expedientes, integraciones evento-a-evento entre plataformas.',
  'params': [{'param_name': 'endpoint_path', 'data_type': 'string', 'required': True, 'group': 'http', 'hint': 'Ruta local que ODM expone para recibir los eventos empujados por la fuente. P. ej. /webhooks/<fuente>.'}]},
 {'name': 'Navegador headless',
  'class_path': 'app.fetchers.headless.HeadlessBrowserFetcher',
  'description': 'Renderiza páginas que cargan sus '
                 'datos por JavaScript (Playwright/Chromium) cuando el scraping HTML estático no ve nada. Casos de '
                 'uso: portales públicos modernos tipo SPA (muchos visores autonómicos y municipales) y aplicaciones '
                 'con tablas alimentadas por una API interna no documentada.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http', 'hint': 'URL de la página a renderizar con JavaScript antes de extraer.'}]},
 {'name': 'OCR PDF',
  'class_path': 'app.fetchers.ocr_pdf.OcrPdfFetcher',
  'description': 'Extrae texto y tablas de PDF que son '
                 'imágenes (sin capa de texto) mediante OCR. Casos de uso: boletines y resoluciones antiguos, BOP '
                 'provinciales escaneados, expedientes digitalizados.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http', 'hint': 'URL del PDF escaneado (imagen sin capa de texto) al que aplicar OCR.'}]},
 {'name': 'Documentos ofimáticos',
  'class_path': 'app.fetchers.office_docs.OfficeDocsFetcher',
  'description': 'Lee tablas y texto de DOCX/XLSX/ODS '
                 'publicados como datos. Casos de uso: anexos de contratación y subvenciones en Excel (p. ej. '
                 'OrganosContratacion.xlsx de PLACSP), memorias y presupuestos en hoja de cálculo.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http', 'hint': 'URL del documento DOCX/XLSX/ODS publicado como dato.'}]},
 {'name': 'Almacenamiento de objetos (S3)',
  'class_path': 'app.fetchers.s3_listing.S3ListingFetcher',
  'description': 'Lista y descarga volcados masivos de '
                 'un bucket compatible con S3/MinIO. Casos de uso: dumps de datos abiertos en buckets públicos y '
                 'mirrors de datasets grandes (Parquet/CSV), habitual en portales internacionales y data lakes.',
  'params': [{'param_name': 'bucket_url', 'data_type': 'string', 'required': True, 'group': 'http', 'hint': 'URL del bucket compatible S3/MinIO. P. ej. s3://<bucket>/<prefijo> o https://<minio>/<bucket>.'}]},
 {'name': 'FTP/SFTP/WebDAV',
  'class_path': 'app.fetchers.file_transfer.FileTransferFetcher',
  'description': 'Transferencia de ficheros por FTP, '
                 'SFTP o WebDAV. Casos de uso: intercambios periódicos entre administraciones y depósitos de '
                 'ficheros estadísticos heredados.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http', 'hint': 'URL del directorio o fichero remoto, esquema según protocolo: ftp://, sftp:// o https:// (WebDAV).'}]},
 {'name': 'gRPC',
  'class_path': 'app.fetchers.grpc.GrpcFetcher',
  'description': 'RPC binario de alto rendimiento '
                 'sobre HTTP/2 (Protocol Buffers). Casos de uso: poco frecuente en datos abiertos; común en '
                 'integraciones internas y entre servicios de plataformas tecnológicas.',
  'params': [{'param_name': 'url', 'data_type': 'string', 'required': True, 'group': 'http', 'hint': 'host:puerto del servicio gRPC. P. ej. <servicio>:443 (TLS) o :50051.'}]}]


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

    # Fidelidad de la fusión REST: el antiguo RestLoopFetcher iteraba por defecto
    # las 52 provincias INE cuando el recurso no traía 'pivot_values' (caso real:
    # Notarías - Guía Notarial). La especie genérica no tiene ese default (y ahora
    # falla en alto sin pivot_values), así que materializamos el default histórico
    # en los recursos ya migrados a pivot_loop que carezcan de él. Idempotente.
    _INE_PROVINCIAS = json.dumps([f"{n:02d}" for n in range(1, 53)])
    db = SessionLocal()
    try:
        reparados = 0
        for rp in db.query(ResourceParam).filter(ResourceParam.key == "pagination", ResourceParam.value == "pivot_loop").all():
            claves_r = {p.key for p in db.query(ResourceParam).filter(ResourceParam.resource_id == rp.resource_id).all()}
            # Solo aplica el default histórico a quien NO tiene ni pivot_values ni
            # fuente de pivotes (el puente DIR3 usa pivot_source_resource y NO debe
            # recibir provincias INE como códigos).
            if claves_r & {"pivot_values", "pivot_source_resource", "pivot_source_odmgr_query"}:
                continue
            db.add(ResourceParam(resource_id=rp.resource_id, key="pivot_values", value=_INE_PROVINCIAS, is_external=False))
            reparados += 1
        if reparados:
            db.commit()
            print(f"[seed_fetchers] pivot_loop sin pivot_values: materializado default histórico (provincias INE) en {reparados} recurso(s)")
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

    # Variantes bajo su especie: el catálogo solo contiene especies; las
    # particularizaciones con nombre viven en fetcher_preset y se eligen por recurso.
    from app.database import SessionLocal as _SL_P
    from app.models import Fetcher as _F_P, Resource as _R_P, FetcherPreset as _FP_P
    from datetime import datetime as _dt_P
    PRESETS = {
        "Feeds ATOM/RSS": [
            {
                "code": "PLACSP CODICE",
                "description": "Sindicaciones de contratación pública en CODICE 2.07 (PLACSP: agregadas, menores, encargos, consultas; Comunidad de Madrid), con cosecha incremental. El recurso aporta la 'url' del feed y la ventana temporal (desde/hasta).",
                "params": {"pagination": "rel_next", "date_field": "fecha", "delay": 2, "timeout": 180, "max_pages": 6, "desde": "auto", "dedup_key": "expediente", "dedup_order_field": "fecha", "field_map": {"expediente": "ContractFolderID", "estado": "ContractFolderStatusCode", "titulo": "title", "objeto": "ProcurementProject/Name", "tipo_codigo": "ProcurementProject/TypeCode", "subtipo_codigo": "ProcurementProject/SubTypeCode", "cpv": "ItemClassificationCode", "importe": "TotalAmount", "valor_estimado": "EstimatedOverallContractAmount", "organo_contratacion": "LocatedContractingParty/PartyName/Name", "provincia": "CountrySubentity", "provincia_codigo": "CountrySubentityCode", "adjudicatario": "WinningParty/PartyName/Name", "nif_adjudicatario": "WinningParty/PartyIdentification/ID", "resultado": "TenderResult/ResultCode", "fecha_adjudicacion": "TenderResult/AwardDate", "num_ofertas": "TenderResult/ReceivedTenderQuantity", "importe_adjudicacion": "TenderResult/AwardedTenderedProject/LegalMonetaryTotal/TaxExclusiveAmount", "fecha": "updated", "url": "link@href"}},
                "locked": ["field_map"],
            },
        ],
        "Web Tree": [
            {
                "code": "Censo documental",
                "description": "Registro documental del árbol: una fila por fichero con sus dimensiones, url, nombre y formato — sin descargar ni parsear nada. El modo honesto para pilas de documentos e informes no tabulares, e insumo directo de catálogos (CKAN/DCAT).",
                "params": {"extract_mode": "censo"},
                "locked": ["extract_mode"],
            },
            {
                "code": "Extracción con receta",
                "description": "Para ficheros-formulario (informes maquetados): aplica las capturas declarativas del param `receta` del recurso y emite UNA fila limpia por fichero (el dato pescado + dimensiones + procedencia). Misma gramática para XLSX y PDF.",
                "params": {"extract_mode": "receta"},
                "locked": ["extract_mode"],
            },
            {
                "code": "Extracción de datos",
                "description": "Descarga cada fichero y lo parsea a filas con el parser tabular compartido (XLSX/CSV/PDF con tabla). Para series cuyos ficheros son tablas de verdad.",
                "params": {"extract_mode": "datos"},
                "locked": ["extract_mode"],
            },
        ],
        "API REST": [
            {
                "code": "CKAN",
                "description": "Catálogo de un portal CKAN (API v3). El recurso aporta la 'url' del buscador del portal (https://<portal>/api/3/action/package_search) y, opcionalmente, una consulta para acotar. Verificado contra opendata.aragon.es.",
                "params": {"pagination": "query_offset", "start_param": "start", "page_size_param": "rows",
                           "page_size": 100, "content_field": "result.results", "id_field": "id", "delay": 1,
                           "headers": {"Accept": "application/json", "User-Agent": "OpenDataManager/1.0"}},
            },
            {
                "code": "DKAN",
                "description": "Catálogo de un portal DKAN (v2). El recurso aporta la 'url' del catálogo del portal (https://<portal>/api/1/metastore/schemas/dataset/items). Verificado contra demo.getdkan.org.",
                "params": {"pagination": "query_offset", "start_param": "offset", "page_size_param": "limit",
                           "page_size": 100, "id_field": "identifier", "delay": 1,
                           "headers": {"Accept": "application/json", "User-Agent": "OpenDataManager/1.0"}},
            },
            {
                "code": "OpenDataSoft",
                "description": "Catálogo de un portal OpenDataSoft (Explore API v2.1). El recurso aporta la 'url' del catálogo del portal (https://<portal>/api/explore/v2.1/catalog/datasets). Verificado contra data.opendatasoft.com.",
                "params": {"pagination": "query_offset", "start_param": "offset", "page_size_param": "limit",
                           "page_size": 100, "content_field": "results", "id_field": "dataset_id", "delay": 1,
                           "headers": {"Accept": "application/json", "User-Agent": "OpenDataManager/1.0"}},
            },
            {
                "code": "Socrata",
                "description": "Catálogo de un portal Socrata. El recurso aporta la 'url' del portal (https://<portal>/api/views/metadata/v1); para un dataset concreto, la misma variante sirve contra /resource/<id>.json. Verificado contra data.cityofnewyork.us.",
                "params": {"pagination": "query_offset", "start_param": "$offset", "page_size_param": "$limit",
                           "page_size": 100, "id_field": "id", "delay": 1,
                           "headers": {"Accept": "application/json", "User-Agent": "OpenDataManager/1.0"}},
            },
            {
                "code": "Paginada",
                "description": "Recorrido por número de página (page=N) hasta página vacía. El recurso aporta la 'url' y, si el API no empieza en la página 1, su 'start_page'.",
                "params": {"pagination": "page_number", "request": "query", "extraction": "passthrough"},
            },
            {
                "code": "Loop de pivotes",
                "description": "Una petición por cada valor de una lista (provincias, códigos...) enviada en el cuerpo JSON. El recurso aporta la 'url', el nombre del parámetro pivote y la lista de valores o el dataset del que tomarlos.",
                "params": {"request": "json_body", "pagination": "pivot_loop", "extraction": "passthrough"},
            },
            {
                "code": "Pivote por valor (query)",
                "description": "Una petición por cada valor de un pivote, enviado como parámetro de QUERY, uniendo y deduplicando (id_field) entre iteraciones. Para endpoints que NO se enumeran de una sola vez: parten por una dimensión (p. ej. /organos por idAdmon=C/A/L/O) o son búsqueda-por-término (p. ej. /terceros por 'busqueda'). Los valores salen de: lista inline (pivot_values), generador combinatorio (pivot_generate=product + pivot_length, p. ej. AAA..ZZZ) o un dataset ODM (pivot_source_*). El recurso aporta url, pivot_param, content_field e id_field; opcional pivot_field_out para etiquetar cada fila con su pivote.",
                "params": {"request": "query", "pagination": "pivot_loop", "extraction": "passthrough"},
            },
            {
                "code": "Series temporales JSON",
                "description": "Respuesta JSON de series temporales aplanada a formato largo (una fila por punto de la serie). El recurso aporta la 'url' y la raíz donde viven las series.",
                "params": {"request": "query", "pagination": "none", "extraction": "timeseries_long"},
            },
        ],
    }
    db = _SL_P()
    try:
        for especie_code, perfiles in PRESETS.items():
            esp = db.query(_F_P).filter(_F_P.code == especie_code).first()
            if esp is None:
                print(f"[seed_fetchers] AVISO: especie '{especie_code}' no existe; presets omitidos")
                continue
            for pdef in perfiles:
                row = db.query(_FP_P).filter(_FP_P.fetcher_id == esp.id, _FP_P.code == pdef["code"]).first()
                bloqueados = [k for k in pdef.get("locked", []) if k in pdef["params"]]
                if row is None:
                    # Inserción tolerante a siembra concurrente (durante el recreate
                    # del deploy, contenedor viejo y nuevo siembran a la vez): si otro
                    # seeder ganó la carrera e insertó esta variante, el savepoint
                    # revienta con IntegrityError; se reconvierte en update idempotente.
                    from sqlalchemy.exc import IntegrityError as _IE
                    try:
                        with db.begin_nested():
                            db.add(_FP_P(fetcher_id=esp.id, code=pdef["code"],
                                         description=pdef.get("description"), params=pdef["params"],
                                         locked_params=bloqueados))
                        print(f"[seed_fetchers] preset '{pdef['code']}' creado bajo '{especie_code}'")
                    except _IE:
                        row = db.query(_FP_P).filter(_FP_P.fetcher_id == esp.id, _FP_P.code == pdef["code"]).first()
                if row is not None:
                    row.description = pdef.get("description")
                    row.params = pdef["params"]
                    row.locked_params = bloqueados
                    row.deleted_at = None
        db.commit()

        # Migración: la fila-variante 'PLACSP CODICE (ATOM)' deja de ser un fetcher.
        # Sus recursos pasan a la especie 'Feeds ATOM/RSS' + preset 'PLACSP CODICE'
        # y la fila se retira. Autodesarmable: sin fila-variante viva, no hace nada.
        variante = db.query(_F_P).filter(_F_P.code == "PLACSP CODICE (ATOM)", _F_P.deleted_at.is_(None)).first()
        if variante is not None:
            esp = db.query(_F_P).filter(_F_P.code == "Feeds ATOM/RSS").first()
            preset = db.query(_FP_P).filter(_FP_P.fetcher_id == esp.id, _FP_P.code == "PLACSP CODICE",
                                            _FP_P.deleted_at.is_(None)).first()
            movidos = 0
            for r in db.query(_R_P).filter(_R_P.fetcher_id == variante.id).all():
                r.fetcher_id = esp.id
                r.preset_id = preset.id
                movidos += 1
            variante.deleted_at = _dt_P.utcnow()
            db.commit()
            print(f"[seed_fetchers] variante 'PLACSP CODICE (ATOM)' → preset: {movidos} recurso(s) repuntados, fila retirada del catálogo")

        # Migración: la fusión REST copió a cada recurso el paquete de params de su
        # antigua especie (Paginada / REST Loop / JSON Time Series). Ahora que esos
        # paquetes SON variantes, asignamos la variante a los recursos de 'API REST'
        # sin preset cuyos params copiados coinciden con el paquete, y desinflamos
        # esos params (solo los idénticos: comportamiento intacto; cualquier valor
        # divergente se queda como override del recurso). Autodesarmable.
        from app.models import ResourceParam as _RP_P
        esp_rest = db.query(_F_P).filter(_F_P.code == "API REST", _F_P.deleted_at.is_(None)).first()
        if esp_rest is not None:
            _PAQUETES = {
                "Paginada": {"pagination": "page_number", "request": "query", "extraction": "passthrough"},
                "Loop de pivotes": {"request": "json_body", "pagination": "pivot_loop", "extraction": "passthrough"},
                "Series temporales JSON": {"request": "query", "pagination": "none", "extraction": "timeseries_long"},
            }
            asignados = {}
            for r in db.query(_R_P).filter(_R_P.fetcher_id == esp_rest.id,
                                           _R_P.preset_id.is_(None),
                                           _R_P.deleted_at.is_(None)).all():
                rps = db.query(_RP_P).filter(_RP_P.resource_id == r.id).all()
                valores = {p.key: p.value for p in rps}
                for code, paquete in _PAQUETES.items():
                    if all(valores.get(k) == v for k, v in paquete.items()):
                        preset = db.query(_FP_P).filter(_FP_P.fetcher_id == esp_rest.id, _FP_P.code == code,
                                                        _FP_P.deleted_at.is_(None)).first()
                        if preset is None:
                            break
                        r.preset_id = preset.id
                        for p in rps:
                            if p.key in paquete and p.value == paquete[p.key]:
                                db.delete(p)
                        asignados[code] = asignados.get(code, 0) + 1
                        break
            if asignados:
                db.commit()
                print(f"[seed_fetchers] paquetes de la fusión REST → variantes asignadas: {asignados}")
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
        # Capacidad de modos por especie (keystone Collections): Web Tree descubre.
        _MODOS = {"Web Tree": ["extraer", "descubrir"], "Catálogo DCAT": ["extraer", "descubrir"], "Pivote": ["descubrir"], "Compressed File": ["extraer", "descubrir"], "Descubridor REST": ["descubrir"]}
        for _f in db.query(Fetcher).filter(Fetcher.deleted_at.is_(None)).all():
            _f.modos = _MODOS.get(_f.code, ["extraer"])
        db.commit()

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

    # Decisión de diseño 2026-06-06 (docs/PENDIENTE_recursos_derivados.md): los
    # joins no viven en la plataforma. Retirada idempotente del recurso derivado
    # 'Órganos Convocantes con DIR3' (su cruce pasa al consumidor) y, al quedar
    # sin recursos, la especie 'Cruce de datasets' cae en la poda anterior en la
    # siguiente pasada — la adelantamos aquí para que un solo arranque baste.
    db = SessionLocal()
    try:
        from datetime import datetime as _dt
        derivado = (db.query(Resource)
                      .filter(Resource.name == "BDNS - Órganos Convocantes con DIR3 (derivado)",
                              Resource.deleted_at.is_(None)).first())
        if derivado is not None:
            derivado.active = False
            derivado.deleted_at = _dt.utcnow()
            db.commit()
            print("[seed_fetchers] retirado el recurso derivado 'Órganos con DIR3' (joins → consumidor)")
        especie = db.query(Fetcher).filter(Fetcher.code == "Cruce de datasets",
                                           Fetcher.deleted_at.is_(None)).first()
        if especie is not None and not [r for r in especie.resources if r.deleted_at is None]:
            especie.deleted_at = _dt.utcnow()
            db.commit()
            print("[seed_fetchers] retirada la especie 'Cruce de datasets'")
    finally:
        db.close()

    print(f"[seed_fetchers] catálogo sincronizado: {len(FETCHERS)} fetchers base")


if __name__ == "__main__":
    try:
        seed()
    except Exception as exc:
        print(f"[seed_fetchers] ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
