"""
Seed 01 — Fetcher types.

Inserts/updates all known fetcher types.
Safe to run multiple times (upsert by name).

Run standalone:
    python -m scripts.seeds.fetchers
"""
from sqlalchemy import text
from scripts.seeds._db import get_session

FETCHERS = [
    {
        "name": "API REST",
        "class_path": "app.fetchers.rest.RestFetcher",
        "description": "API RESTful con soporte para JSON/XML",
    },
    {
        "name": "API REST Paginada",
        "class_path": "app.fetchers.paginated_rest.PaginatedRestFetcher",
        "description": (
            "Fetcher para APIs REST JSON con paginación por offset. "
            "Itera páginas automáticamente hasta obtener todos los registros. "
            "Soporta paginación por page/pageSize, campo de contenido configurable, "
            "deduplicación por ID y límite de seguridad de páginas. "
            "Usado por BDNS, INE y otras APIs públicas con grandes volúmenes de datos."
        ),
    },
    {
        "name": "CSV desde URL",
        "class_path": "app.fetchers.csv.CSVFetcher",
        "description": "Descarga y parsea ficheros CSV desde una URL directa de descarga.",
    },
    {
        "name": "Feeds ATOM/RSS",
        "class_path": "app.fetchers.atom.AtomFetcher",
        "description": (
            "Fetcher para feeds ATOM y RSS estándar, compatible con ContentAPI de la "
            "Junta de Andalucía y otros portales de datos abiertos que usan sindicación XML. "
            "Soporta paginación OpenSearch (startIndex, itemsPerPage, totalResults) y "
            "parsing de entries ATOM con múltiples campos."
        ),
    },
    {
        "name": "HTML Forms",
        "class_path": "app.fetchers.html.HTMLFetcher",
        "description": "Formularios web HTML (scraping de páginas y formularios)",
    },
    {
        "name": "HTML Paginated",
        "class_path": "app.fetchers.paginated_html.PaginatedHtmlFetcher",
        "description": (
            "Scraper HTML con paginación automática. Soporta múltiples mecanismos de "
            "paginación (links, parámetros de URL), extracción mediante selectores CSS "
            "y configuración completa de headers y delays. "
            "Ideal para portales gubernamentales con resultados paginados."
        ),
    },
    {
        "name": "HTML SearchLoop",
        "class_path": "app.fetchers.searchloop_html.SearchLoopHtmlFetcher",
        "description": (
            "Buscadores HTML que pivotan sobre los valores de un <select>: "
            "descubre las opciones automáticamente e itera sobre cada una, "
            "con soporte para paginación por link."
        ),
    },
    {
        "name": "Portales CKAN",
        "class_path": "app.fetchers.ckan.CKANFetcher",
        "description": (
            "Fetcher genérico para portales CKAN (Comprehensive Knowledge Archive Network). "
            "Soporta datos.gob.es, data.gov, data.gov.uk y cualquier portal basado en CKAN. "
            "Permite extraer datasets, recursos y metadatos desde cualquier portal que "
            "implemente la API CKAN estándar."
        ),
    },
    {
        "name": "Servicios Geográficos",
        "class_path": "app.fetchers.geo.GeoFetcher",
        "description": (
            "Fetcher universal para datos geográficos y geoespaciales. "
            "Soporta estándares OGC (WFS, WMS) y formatos GeoJSON, Shapefile. "
            "Ideal para catastro, límites administrativos, cartografía, mapas base y "
            "cualquier tipo de información georreferenciada. "
            "Permite filtrado espacial, transformación de coordenadas y "
            "simplificación de geometrías."
        ),
    },
    {
        "name": "Servicios SOAP/WSDL",
        "class_path": "app.fetchers.soap.SoapFetcher",
        "description": (
            "Fetcher para servicios web SOAP/WSDL. Soporta operaciones SOAP estándar "
            "con autenticación WS-Security. Permite invocar métodos de servicios web "
            "empresariales, procesamiento de WSDL automático, selección de servicios y "
            "puertos específicos, y configuración de timeouts y validación SSL."
        ),
    },
]


def seed(db=None):
    own_session = db is None
    if own_session:
        db = get_session()
    try:
        for f in FETCHERS:
            db.execute(
                text("""
                    INSERT INTO opendata.fetcher (id, name, class_path, description)
                    VALUES (gen_random_uuid(), :name, :class_path, :description)
                    ON CONFLICT (name) DO UPDATE
                        SET class_path  = EXCLUDED.class_path,
                            description = EXCLUDED.description
                """),
                f,
            )
        db.commit()
        print(f"  [fetchers] {len(FETCHERS)} fetchers upserted.")
    except Exception:
        db.rollback()
        raise
    finally:
        if own_session:
            db.close()


if __name__ == "__main__":
    seed()
