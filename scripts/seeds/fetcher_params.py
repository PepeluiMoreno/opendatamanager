"""
Seed 02 — Fetcher type params (type_fetcher_params table).

LEGACY: este script ya no forma parte del bootstrap de despliegue. El catálogo
base de fetchers y sus parámetros se sincroniza vía API administrativa en
`seed_fetchers.py`.

Defines the accepted parameters for each fetcher type.
Safe to run multiple times (upsert by fetcher name + param_name).

Run standalone:
    python -m scripts.seeds.fetcher_params
"""
import json
from sqlalchemy import text
from scripts.seeds._db import get_session

# Each entry: fetcher name → list of param dicts
# Keys: param_name, required, data_type, default_value (optional),
#       enum_values (optional list), description (optional)
FETCHER_PARAMS = {
    "API REST": [
        {"param_name": "url",          "required": True,  "data_type": "string",  "description": "URL del endpoint"},
        {"param_name": "method",       "required": False, "data_type": "enum",    "enum_values": ["GET", "POST", "PUT", "PATCH"], "default_value": "GET", "description": "Método HTTP"},
        {"param_name": "headers",      "required": False, "data_type": "json",    "description": "Cabeceras HTTP (objeto JSON)"},
        {"param_name": "query_params", "required": False, "data_type": "json",    "description": "Parámetros de query string (objeto JSON)"},
        {"param_name": "timeout",      "required": False, "data_type": "integer", "default_value": 30,   "description": "Timeout en segundos"},
        {"param_name": "max_retries",  "required": False, "data_type": "integer", "default_value": 3,    "description": "Reintentos ante fallos"},
        {"param_name": "page-size",    "required": False, "data_type": "integer", "description": "Tamaño de página (si la API lo soporta)"},
    ],

    "API REST Paginada": [
        {"param_name": "url",             "required": True,  "data_type": "string",  "description": "URL base de la API"},
        {"param_name": "method",          "required": False, "data_type": "enum",    "enum_values": ["GET", "POST"], "default_value": "GET", "description": "Método HTTP"},
        {"param_name": "query_params",    "required": False, "data_type": "string",  "description": "Parámetros fijos de query string (JSON)"},
        {"param_name": "headers",         "required": False, "data_type": "string",  "description": "Cabeceras HTTP (JSON)"},
        {"param_name": "page_param",      "required": False, "data_type": "string",  "default_value": "page",     "description": "Nombre del parámetro de página"},
        {"param_name": "page_size_param", "required": False, "data_type": "string",  "default_value": "pageSize", "description": "Nombre del parámetro de tamaño de página"},
        {"param_name": "page_size",       "required": False, "data_type": "integer", "default_value": 100,        "description": "Registros por página"},
        {"param_name": "content_field",   "required": False, "data_type": "string",  "description": "Campo JSON que contiene el array de registros"},
        {"param_name": "id_field",        "required": False, "data_type": "string",  "description": "Campo de ID para deduplicación"},
        {"param_name": "max_pages",       "required": False, "data_type": "integer", "default_value": 500,        "description": "Límite de seguridad de páginas"},
        {"param_name": "delay_between_pages", "required": False, "data_type": "number", "default_value": 0.5,    "description": "Segundos entre páginas"},
        {"param_name": "timeout",         "required": False, "data_type": "integer", "default_value": 60,         "description": "Timeout en segundos"},
    ],

    "CSV desde URL": [
        {"param_name": "url",       "required": True,  "data_type": "string",  "description": "URL directa al fichero CSV"},
        {"param_name": "encoding",  "required": False, "data_type": "string",  "default_value": "utf-8",  "description": "Codificación del fichero"},
        {"param_name": "delimiter", "required": False, "data_type": "string",  "default_value": ",",      "description": "Separador de columnas"},
        {"param_name": "headers",   "required": False, "data_type": "json",    "description": "Cabeceras HTTP adicionales"},
        {"param_name": "timeout",   "required": False, "data_type": "integer", "default_value": 60,       "description": "Timeout en segundos"},
    ],

    "Feeds ATOM/RSS": [
        {"param_name": "base_url",      "required": True,  "data_type": "string",  "description": "URL base de la ContentAPI o feed"},
        {"param_name": "dataset_id",    "required": True,  "data_type": "string",  "description": "Identificador del dataset/feed"},
        {"param_name": "format",        "required": False, "data_type": "enum",    "enum_values": ["atom", "rss"], "default_value": "atom", "description": "Formato del feed"},
        {"param_name": "page_size",     "required": False, "data_type": "integer", "default_value": 50,   "description": "Registros por página"},
        {"param_name": "start_index",   "required": False, "data_type": "integer", "default_value": 0,    "description": "Índice inicial (OpenSearch)"},
        {"param_name": "max_pages",     "required": False, "data_type": "integer", "default_value": 100,  "description": "Límite de páginas"},
        {"param_name": "sort",          "required": False, "data_type": "string",  "description": "Criterio de ordenación (ej: date:desc)"},
        {"param_name": "source_filter", "required": False, "data_type": "string",  "description": "Filtro de fuente de datos"},
        {"param_name": "extract_fields","required": False, "data_type": "json",    "description": "Mapeo de campos a extraer de cada entry"},
        {"param_name": "namespaces",    "required": False, "data_type": "json",    "description": "Namespaces XML adicionales"},
        {"param_name": "verify_ssl",    "required": False, "data_type": "boolean", "default_value": True, "description": "Verificar certificado SSL"},
        {"param_name": "timeout",       "required": False, "data_type": "integer", "default_value": 30,   "description": "Timeout en segundos"},
    ],

    "HTML Forms": [
        {"param_name": "url",                   "required": True,  "data_type": "string",  "description": "URL del buscador/formulario"},
        {"param_name": "rows_selector",         "required": True,  "data_type": "string",  "description": "Selector CSS de filas de resultados"},
        {"param_name": "has_header",            "required": False, "data_type": "boolean", "default_value": True, "description": "Primera fila es cabecera"},
        {"param_name": "pagination_type",       "required": False, "data_type": "string",  "description": "Tipo de paginación (link, param...)"},
        {"param_name": "max_pages",             "required": False, "data_type": "integer", "default_value": 50,   "description": "Límite de páginas"},
        {"param_name": "delay_between_requests","required": False, "data_type": "integer", "default_value": 1,    "description": "Segundos entre peticiones"},
        {"param_name": "clean_html",            "required": False, "data_type": "boolean", "default_value": True, "description": "Limpiar HTML de celdas"},
    ],

    "HTML Paginated": [
        {"param_name": "url",                  "required": True,  "data_type": "string",  "description": "URL del buscador con paginación"},
        {"param_name": "rows_selector",        "required": True,  "data_type": "string",  "description": "Selector CSS de filas de resultados"},
        {"param_name": "method",               "required": False, "data_type": "enum",    "enum_values": ["GET", "POST"], "default_value": "GET", "description": "Método HTTP del formulario"},
        {"param_name": "extra_params",         "required": False, "data_type": "json",    "description": "Parámetros fijos adicionales del formulario"},
        {"param_name": "next_page_selector",   "required": False, "data_type": "string",  "description": "Selector CSS del enlace 'siguiente'"},
        {"param_name": "max_pages",            "required": False, "data_type": "integer", "default_value": 100,   "description": "Límite de páginas"},
        {"param_name": "has_header",           "required": False, "data_type": "boolean", "default_value": True,  "description": "Primera fila es cabecera"},
        {"param_name": "delay_between_pages",  "required": False, "data_type": "number",  "default_value": 0.5,   "description": "Segundos entre páginas"},
        {"param_name": "headers",              "required": False, "data_type": "json",    "description": "Cabeceras HTTP adicionales"},
        {"param_name": "timeout",              "required": False, "data_type": "integer", "default_value": 30,    "description": "Timeout en segundos"},
        {"param_name": "max_retries",          "required": False, "data_type": "integer", "default_value": 3,     "description": "Reintentos por petición"},
    ],

    "HTML SearchLoop": [
        {"param_name": "url",                    "required": True,  "data_type": "string",  "description": "URL del formulario de búsqueda"},
        {"param_name": "search_field_name",      "required": True,  "data_type": "string",  "description": "Atributo name/id del <select> a pivotar"},
        {"param_name": "rows_selector",          "required": True,  "data_type": "string",  "description": "Selector CSS de filas de resultados"},
        {"param_name": "method",                 "required": False, "data_type": "enum",    "enum_values": ["GET", "POST"], "default_value": "GET", "description": "Método HTTP del formulario"},
        {"param_name": "search_field_values",    "required": False, "data_type": "string",  "description": "Override manual de valores (CSV); omitir para auto-discovery"},
        {"param_name": "extra_params",           "required": False, "data_type": "json",    "description": "Parámetros fijos adicionales del formulario"},
        {"param_name": "next_page_selector",     "required": False, "data_type": "string",  "description": "Selector CSS del enlace 'siguiente'"},
        {"param_name": "max_pages",              "required": False, "data_type": "integer", "default_value": 50,    "description": "Límite de páginas por valor del select"},
        {"param_name": "has_header",             "required": False, "data_type": "boolean", "default_value": True,  "description": "Primera fila es cabecera"},
        {"param_name": "delay_between_pages",    "required": False, "data_type": "number",  "default_value": 0.5,   "description": "Segundos entre páginas"},
        {"param_name": "delay_between_searches", "required": False, "data_type": "number",  "default_value": 1.0,   "description": "Segundos entre valores del select"},
        {"param_name": "stop_on_error",          "required": False, "data_type": "boolean", "default_value": False, "description": "Detener la ejecución si un valor falla"},
        {"param_name": "headers",                "required": False, "data_type": "json",    "description": "Cabeceras HTTP adicionales"},
        {"param_name": "timeout",                "required": False, "data_type": "integer", "default_value": 30,    "description": "Timeout por petición en segundos"},
        {"param_name": "max_retries",            "required": False, "data_type": "integer", "default_value": 3,     "description": "Reintentos por petición"},
    ],

    "Portales CKAN": [
        {"param_name": "base_url",        "required": True,  "data_type": "string",  "description": "URL base del portal CKAN (ej: https://datos.gob.es)"},
        {"param_name": "organization",    "required": False, "data_type": "string",  "description": "Filtrar por organización publicadora"},
        {"param_name": "format",          "required": False, "data_type": "enum",    "enum_values": ["JSON", "CSV", "XML", "RDF"], "description": "Filtrar por formato de recurso"},
        {"param_name": "limit",           "required": False, "data_type": "integer", "default_value": 1000, "description": "Registros por página"},
        {"param_name": "include_private", "required": False, "data_type": "boolean", "default_value": False, "description": "Incluir datasets privados (requiere api_key)"},
        {"param_name": "api_key",         "required": False, "data_type": "string",  "description": "API key para portales con autenticación"},
    ],

    "Servicios Geográficos": [
        {"param_name": "url",              "required": True,  "data_type": "string",  "description": "URL del servicio WFS/WMS/GeoJSON"},
        {"param_name": "service_type",     "required": True,  "data_type": "enum",    "enum_values": ["WFS", "WMS", "GeoJSON", "Shapefile"], "description": "Tipo de servicio geográfico"},
        {"param_name": "layer",            "required": False, "data_type": "string",  "description": "Nombre de la capa a extraer"},
        {"param_name": "version",          "required": False, "data_type": "enum",    "enum_values": ["1.0.0", "1.1.0", "2.0.0"], "description": "Versión del protocolo OGC"},
        {"param_name": "output_format",    "required": False, "data_type": "enum",    "enum_values": ["GeoJSON", "GML", "CSV"], "description": "Formato de salida"},
        {"param_name": "crs",              "required": False, "data_type": "enum",    "enum_values": ["EPSG:4326", "EPSG:25830", "EPSG:3857"], "description": "Sistema de referencia de coordenadas"},
        {"param_name": "bbox",             "required": False, "data_type": "string",  "description": "Bounding box de filtrado espacial (minX,minY,maxX,maxY)"},
        {"param_name": "property_filter",  "required": False, "data_type": "string",  "description": "Filtro CQL/OGC sobre propiedades"},
        {"param_name": "max_features",     "required": False, "data_type": "integer", "description": "Límite de features a extraer"},
        {"param_name": "simplify_geometry","required": False, "data_type": "boolean", "default_value": False, "description": "Simplificar geometrías"},
        {"param_name": "tolerance",        "required": False, "data_type": "number",  "description": "Tolerancia de simplificación (grados/metros)"},
    ],

    "Servicios SOAP/WSDL": [
        {"param_name": "wsdl_url",     "required": True,  "data_type": "string",  "description": "URL del fichero WSDL"},
        {"param_name": "operation",    "required": True,  "data_type": "string",  "description": "Nombre de la operación SOAP a invocar"},
        {"param_name": "service_name", "required": False, "data_type": "string",  "description": "Nombre del servicio (si el WSDL define varios)"},
        {"param_name": "port_name",    "required": False, "data_type": "string",  "description": "Nombre del puerto de binding"},
        {"param_name": "username",     "required": False, "data_type": "string",  "description": "Usuario para WS-Security"},
        {"param_name": "password",     "required": False, "data_type": "string",  "description": "Contraseña para WS-Security"},
        {"param_name": "verify_ssl",   "required": False, "data_type": "boolean", "default_value": True, "description": "Verificar certificado SSL"},
        {"param_name": "timeout",      "required": False, "data_type": "integer", "default_value": 30,   "description": "Timeout en segundos"},
    ],
}


def seed(db=None):
    own_session = db is None
    if own_session:
        db = get_session()

    total = 0
    try:
        for fetcher_name, params in FETCHER_PARAMS.items():
            row = db.execute(
                text("SELECT id FROM opendata.fetcher WHERE name = :name"),
                {"name": fetcher_name},
            ).fetchone()
            if not row:
                print(f"  [fetcher_params] WARNING: fetcher '{fetcher_name}' not found — skipping its params.")
                continue

            fetcher_id = row[0]
            for p in params:
                default_val = p.get("default_value")
                enum_vals   = p.get("enum_values")
                db.execute(
                    text("""
                        INSERT INTO opendata.type_fetcher_params
                            (id, fetcher_id, param_name, required, data_type,
                             default_value, enum_values, description)
                        SELECT
                            gen_random_uuid(), :fetcher_id, :param_name, :required, :data_type,
                            CAST(:default_value AS jsonb), CAST(:enum_values AS jsonb), :description
                        WHERE NOT EXISTS (
                            SELECT 1 FROM opendata.type_fetcher_params
                            WHERE fetcher_id = :fetcher_id AND param_name = :param_name
                        )
                    """),
                    {
                        "fetcher_id":    fetcher_id,
                        "param_name":    p["param_name"],
                        "required":      p.get("required", False),
                        "data_type":     p.get("data_type", "string"),
                        "default_value": json.dumps(default_val) if default_val is not None else None,
                        "enum_values":   json.dumps(enum_vals)   if enum_vals   is not None else None,
                        "description":   p.get("description"),
                    },
                )
                total += 1

        db.commit()
        print(f"  [fetcher_params] {total} params processed.")
    except Exception:
        db.rollback()
        raise
    finally:
        if own_session:
            db.close()


if __name__ == "__main__":
    seed()
