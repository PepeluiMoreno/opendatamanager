"""
Clasificación de origen de fuentes y política de admisión.

Operacionaliza la decisión de gobernanza: ODM solo aloja datos de organismos
públicos / de derecho público, MÁS fuentes abiertas por licencia. Lo privado y el
scraping no autorizado quedan fuera.

Dos conceptos:
  - clase_fuente: CÓMO se obtiene el dato (eje técnico/origen).
  - admisión: si esa clase es aceptable en esta instancia (política configurable).

El eje de autorización legal (robots.txt, permiso explícito) es complementario y
vive en su propio mecanismo; aquí se clasifica el origen y se aplica la política
de clases admitidas.
"""
import os
from typing import List, Optional

# Clases de origen
API_ABIERTA = "api_abierta"               # API abierta y documentada (REST/SOAP/WFS/OSM)
PUBLICACION_ABIERTA = "publicacion_abierta"  # ficheros/feeds publicados (descargas, ATOM, OSM dumps)
SCRAPING_PUBLICO = "scraping_publico"     # scraping de fuente pública sin API
SCRAPING_PRIVADO = "scraping_privado"     # scraping/explotación de fuente privada o de pago

ABIERTAS = frozenset({API_ABIERTA, PUBLICACION_ABIERTA})
SCRAPING = frozenset({SCRAPING_PUBLICO, SCRAPING_PRIVADO})

# Fetchers cuyo transporte es scraping de páginas (no API/feed/fichero).
_FETCHERS_SCRAPING = frozenset({
    "HTML Form", "HTML Paginated", "HTML SearchLoop", "Web Tree",
    "URL Loop HTML", "HTML (genérico)", "Power BI", "PDF Table",
})
# Fetchers de publicación abierta (ficheros/feeds estáticos).
_FETCHERS_PUBLICACION = frozenset({
    "File Download", "Compressed File", "Feeds ATOM/RSS", "OSM Overpass", "XBRL",
})
# Fetchers de API abierta.
_FETCHERS_API = frozenset({
    "API REST", "API REST Paginada", "REST Loop", "SOAP", "WFS", "WMS",
    "JSON Time Series",
})


def es_abierto(clase: Optional[str]) -> bool:
    return clase in ABIERTAS


def clasificar(publisher_nivel: Optional[str], fetcher_code: Optional[str]) -> Optional[str]:
    """Heurística de clasificación (publisher, fetcher) -> clase_fuente.

    Devuelve None ("sin clasificar") para fetchers desconocidos, para forzar
    revisión manual en vez de una clasificación silenciosa errónea.
    """
    if (publisher_nivel or "").upper() == "PRIVADO":
        return SCRAPING_PRIVADO
    if fetcher_code in _FETCHERS_SCRAPING:
        return SCRAPING_PUBLICO
    if fetcher_code in _FETCHERS_PUBLICACION:
        return PUBLICACION_ABIERTA
    if fetcher_code in _FETCHERS_API:
        return API_ABIERTA
    return None


def clases_admitidas() -> List[str]:
    """Clases que esta instancia acepta, desde ODM_ALLOWED_SOURCE_CLASSES (CSV).

    Por defecto, solo las abiertas: lo privado/scraping queda fuera salvo que el
    operador lo amplíe explícitamente.
    """
    env = os.environ.get("ODM_ALLOWED_SOURCE_CLASSES")
    if not env:
        return list(ABIERTAS)
    return [c.strip() for c in env.split(",") if c.strip()]


def admite(clase: Optional[str]) -> bool:
    """¿Se admite una fuente de esta clase? (sin clasificar -> no, por prudencia)."""
    if clase is None:
        return False
    return clase in clases_admitidas()
