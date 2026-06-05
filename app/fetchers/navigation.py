"""Categoría de variación NAVEGACIÓN / DESCUBRIMIENTO (sabor HTML).

La categoría que REST no tiene: cómo se generan y enlazan las páginas a visitar.
Aquí viven las partes PURAS y testeables —resolver valores de pivote, construir
URLs por plantilla, detectar el enlace 'siguiente' en el HTML—. La orquestación que
hace HTTP (recorrido recursivo por niveles, árbol de directorios, pivote desde una
consulta GraphQL de ODM) vive en el fetcher genérico, que se apoya en estos helpers.

Las clases html / paginated_html / searchloop_html / url_loop_html comparten estos
ladrillos hoy reimplementados de forma divergente.
"""
import json
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin
from bs4 import BeautifulSoup


def pivot_values(params: Dict[str, Any]) -> List[str]:
    """Lista de valores de pivote (un <select>, una lista literal o CSV)."""
    raw = params.get("search_field_values", params.get("pivot_values"))
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(v) for v in raw]
    s = str(raw).strip()
    if not s:
        return []
    if s.startswith("["):
        try:
            return [str(v) for v in json.loads(s)]
        except json.JSONDecodeError:
            pass
    return [v.strip() for v in s.split(",") if v.strip()]


def build_url(template: str, value: Any = None, page: Any = None) -> str:
    """Sustituye {value} y {page} en la plantilla (tolerante: ignora otras llaves)."""
    out = template or ""
    if value is not None:
        out = out.replace("{value}", str(value))
    if page is not None:
        out = out.replace("{page}", str(page))
    return out


def paged_urls(template: str, value: Any, start_page: int, max_pages: int) -> List[str]:
    """URLs paginadas por plantilla {page} (acotadas por max_pages)."""
    return [build_url(template, value=value, page=p)
            for p in range(start_page, start_page + max(0, max_pages))]


def next_link(soup_or_html: Union[BeautifulSoup, str],
              selectors: Union[str, List[str], None],
              attr: str = "href",
              base_url: Optional[str] = None) -> Optional[str]:
    """Primer enlace 'siguiente' según una lista de selectores CSS, resuelto contra base_url."""
    soup = (soup_or_html if isinstance(soup_or_html, BeautifulSoup)
            else BeautifulSoup(soup_or_html or "", "html.parser"))
    if isinstance(selectors, str):
        selectors = [selectors]
    for sel in (selectors or []):
        el = soup.select_one(sel)
        if el:
            href = el.get(attr)
            if href:
                return urljoin(base_url, href) if base_url else href
    return None


def follow_links(soup_or_html: Union[BeautifulSoup, str],
                 selector: str,
                 attr: str = "href",
                 base_url: Optional[str] = None) -> List[str]:
    """Todas las URLs de sub-páginas indicadas por un selector (para niveles/árbol)."""
    if not selector:
        return []
    soup = (soup_or_html if isinstance(soup_or_html, BeautifulSoup)
            else BeautifulSoup(soup_or_html or "", "html.parser"))
    urls = []
    for a in soup.select(selector):
        href = a.get(attr)
        if href:
            urls.append(urljoin(base_url, href) if base_url else href)
    return urls
