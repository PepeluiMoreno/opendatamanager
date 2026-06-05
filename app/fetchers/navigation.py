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


def form_next(soup_or_html: Union[BeautifulSoup, str],
              selectors: Union[str, List[str], None],
              page_param: str = "pagina",
              base_url: Optional[str] = None):
    """Paginación por re-envío de formulario (buscadores con estado, p. ej. RER).
    Localiza el formulario de paginación, recoge TODOS sus input/select e
    incrementa page_param. Devuelve (url_destino, inputs) o None si no hay
    formulario. Portado fielmente de PaginatedHtmlFetcher (pagination_type=form)."""
    soup = (soup_or_html if isinstance(soup_or_html, BeautifulSoup)
            else BeautifulSoup(soup_or_html or "", "html.parser"))
    if isinstance(selectors, str):
        s = selectors.strip()
        if s.startswith("["):
            import json as _j
            try:
                selectors = _j.loads(s)
            except Exception:
                selectors = [s]
        else:
            selectors = [x.strip() for x in s.split(",") if x.strip()]
    form = None
    for sel in (selectors or ["form"]):
        form = soup.select_one(sel)
        if form:
            break
    if form is None:
        return None
    inputs = {}
    for inp in form.find_all(["input", "select"]):
        name = inp.get("name")
        if name:
            inputs[name] = inp.get("value", "") or ""
    try:
        actual = int(inputs.get(page_param, 1) or 1)
    except (TypeError, ValueError):
        actual = 1
    inputs[page_param] = str(actual + 1)
    action = form.get("action") or ""
    destino = urljoin(base_url, action) if (base_url and action) else (action or base_url)
    return destino, inputs
