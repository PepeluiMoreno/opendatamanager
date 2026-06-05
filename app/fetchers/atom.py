"""
AtomFetcher - Fetcher para feeds ATOM/RSS.

Soporta:
- Feeds ATOM 1.0 (RFC 4287)
- Feeds RSS 2.0
- Paginación via parámetros de query (start_index / page)

Params configurables via ResourceParam:
    url           URL del feed (obligatorio)
    method        Método HTTP (default: get)
    page_size     Entradas por página (default: 50)
    start_param   Nombre del param de offset (default: start_index)
    page_size_param Nombre del param de tamaño (default: page_size)
    max_pages     Límite de seguridad (default: 0 = sin límite)
    query_params  Params fijos adicionales como JSON string
    headers       Headers adicionales como JSON string
    timeout       Timeout en segundos (default: 30)
    entry_tag     Tag XML de cada entrada (default: autodetect)
"""
import json
import logging
import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from app.fetchers.base import BaseFetcher, RawData, ParsedData, DomainData

logger = logging.getLogger(__name__)

# Namespaces ATOM y RSS comunes
_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "media": "http://search.yahoo.com/mrss/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "georss": "http://www.georss.org/georss",
}


def _tag_local(tag: str) -> str:
    """Quita el namespace de un tag XML: {ns}name → name"""
    return tag.split("}")[-1] if "}" in tag else tag


def _element_to_dict(element: ET.Element) -> Dict[str, Any]:
    """Convierte un elemento XML a dict recursivamente."""
    result: Dict[str, Any] = {}

    # Atributos del elemento
    if element.attrib:
        for k, v in element.attrib.items():
            result[f"@{_tag_local(k)}"] = v

    # Texto directo
    text = (element.text or "").strip()

    children = list(element)
    if not children:
        return text if text else result

    for child in children:
        key = _tag_local(child.tag)
        value = _element_to_dict(child)
        if key in result:
            # Convertir a lista si hay duplicados
            existing = result[key]
            if not isinstance(existing, list):
                result[key] = [existing]
            result[key].append(value)
        else:
            result[key] = value

    if text:
        result["_text"] = text

    return result


def _parse_feed_entries(root: ET.Element) -> List[Dict[str, Any]]:
    """Extrae entries/items del feed independientemente del formato."""
    # ATOM 1.0: <feed> con <entry>
    entries = root.findall("atom:entry", _NS)
    if entries:
        return [_element_to_dict(e) for e in entries]

    # ATOM sin namespace explícito
    entries = root.findall("{http://www.w3.org/2005/Atom}entry")
    if entries:
        return [_element_to_dict(e) for e in entries]

    # RSS 2.0: <rss><channel><item>
    channel = root.find("channel")
    if channel is not None:
        items = channel.findall("item")
        if items:
            return [_element_to_dict(i) for i in items]

    # Fallback: cualquier tag <entry> o <item>
    for tag in ("entry", "item"):
        found = root.findall(f".//{tag}")
        if found:
            return [_element_to_dict(e) for e in found]

    return []


def _entry_elements(root: ET.Element) -> List[ET.Element]:
    """Devuelve los elementos entry/item del feed (cualquier formato)."""
    ns = "{http://www.w3.org/2005/Atom}"
    els = root.findall(f"{ns}entry") or root.findall("entry")
    if not els:
        ch = root.find("channel")
        if ch is not None:
            els = ch.findall("item")
    if not els:
        for tag in ("entry", "item"):
            els = root.findall(f".//{tag}")
            if els:
                break
    return els


def _first_by_path(el: ET.Element, path: str):
    """Resuelve una ruta de nombres locales (p. ej. 'ProcurementProject/Name'),
    descendiendo al primer hijo que casa en cada nivel. Sintaxis 'tag@attr' para
    leer un atributo. Robusto al namespace (compara por nombre local)."""
    cur = el
    parts = path.split("/")
    for i, part in enumerate(parts):
        attr = None
        if "@" in part:
            part, attr = part.split("@", 1)
        encontrado = None
        for d in cur.iter():
            if d is not cur and _tag_local(d.tag) == part:
                encontrado = d
                break
        if encontrado is None:
            return None
        cur = encontrado
        if i == len(parts) - 1:
            if attr:
                return cur.get(attr)
            return (cur.text or "").strip() or None
    return None


def _extract_flat(el: ET.Element, field_map: Dict[str, str]) -> Dict[str, Any]:
    """Aplana un elemento a un registro según el mapa {campo_salida: ruta}."""
    return {salida: _first_by_path(el, ruta) for salida, ruta in field_map.items()}


def _parse_dt(valor: Optional[str]):
    """Parsea una fecha ISO 8601 (con o sin hora/zona) a datetime. None si no se puede."""
    if not valor:
        return None
    from datetime import datetime
    s = str(valor).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        # fecha sola u otros formatos cortos
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y"):
            try:
                return datetime.strptime(s[:19], fmt)
            except ValueError:
                continue
    return None


def _filtrar_por_fecha(batch, date_field: str, desde, hasta=None):
    """Conserva entradas dentro de la ventana temporal [desde, hasta] (las de fecha
    desconocida se conservan por prudencia). Devuelve (conservadas, frontera_alcanzada).
    Asume feed en orden descendente: una entrada con fecha < desde marca la frontera
    (ya hemos llegado a lo viejo); una entrada con fecha > hasta simplemente se
    descarta y se sigue paginando hacia atrás hasta entrar en la ventana.

    Compara de forma 'naive' (sin zona) para evitar errores aware/naive."""
    if desde is None and hasta is None:
        return batch, False
    desde_cmp = desde.replace(tzinfo=None) if desde else None
    hasta_cmp = hasta.replace(tzinfo=None) if hasta else None
    conservadas = []
    frontera = False
    for rec in batch:
        d = _parse_dt(rec.get(date_field) if isinstance(rec, dict) else None)
        if d is None:
            conservadas.append(rec)  # sin fecha → no se descarta
            continue
        d = d.replace(tzinfo=None)
        if desde_cmp and d < desde_cmp:
            frontera = True
            continue
        if hasta_cmp and d > hasta_cmp:
            continue
        conservadas.append(rec)
    return conservadas, frontera


def _next_link(root: ET.Element) -> Optional[str]:
    ns = "{http://www.w3.org/2005/Atom}"
    for link in root.findall(f"{ns}link") or root.findall("link"):
        if link.get("rel") == "next":
            return link.get("href")
    return None


class AtomFetcher(BaseFetcher):

    def fetch(self) -> RawData:
        url = self.params.get("url")
        if not url:
            raise ValueError("El parámetro 'url' es obligatorio para AtomFetcher")

        method = self.params.get("method", "get").upper()
        page_size = int(self.params.get("page_size", 50))
        start_param = self.params.get("start_param", "start_index")
        page_size_param = self.params.get("page_size_param", "page_size")
        max_pages = int(self.params.get("max_pages", 0))
        timeout = int(self.params.get("timeout", 30))
        preview_limit = int(self.params.get("_preview_limit", 0))

        fixed_params = self.params.get("query_params", {})
        if isinstance(fixed_params, str):
            fixed_params = json.loads(fixed_params)

        headers = self.params.get("headers", {})
        if isinstance(headers, str):
            headers = json.loads(headers)

        effective_page_size = min(page_size, preview_limit) if preview_limit else page_size

        # Mapa de aplanado opcional: {campo_salida: ruta_local}. Si no se define,
        # cada entry se devuelve como dict anidado genérico (comportamiento previo).
        field_map = self.params.get("field_map")
        if isinstance(field_map, str):
            field_map = json.loads(field_map) if field_map.strip() else None

        # Modo de paginación: 'query' (offset por query-params, por defecto) o
        # 'rel_next' (sigue <link rel="next">, típico de sindicaciones).
        pagination = (self.params.get("pagination", "query") or "query").lower()
        delay = float(self.params.get("delay", 0))

        # Parada incremental por fecha: 'desde' (ISO) marca el suelo temporal; se
        # filtran las entradas anteriores y se deja de paginar al alcanzarlas
        # (los feeds van en orden descendente). 'desde=auto' usa la marca de agua
        # inyectada por el manager en '_watermark' (máximo de la ejecución previa).
        date_field = self.params.get("date_field", "fecha")
        desde_raw = self.params.get("desde") or None       # "" equivale a ausente
        if desde_raw == "auto":
            desde_raw = self.params.get("_watermark")
        desde = _parse_dt(desde_raw)
        hasta = _parse_dt(self.params.get("hasta") or None)  # techo opcional de la ventana
        if desde or hasta:
            logger.info(f"  ventana temporal: desde={desde.isoformat() if desde else '—'} "
                        f"hasta={hasta.isoformat() if hasta else '—'}")

        def _entradas(root):
            if field_map:
                return [_extract_flat(e, field_map) for e in _entry_elements(root)]
            return _parse_feed_entries(root)

        all_records: List[Dict[str, Any]] = []
        page = 0
        logger.info(f"Iniciando fetch ATOM: {url} (paginación={pagination})")
        session = requests.Session()

        if pagination == "rel_next":
            import time
            next_url: Optional[str] = url
            while next_url:
                response = self._request(session, method, next_url, headers=headers, timeout=timeout)
                response.raise_for_status()
                root = ET.fromstring(response.text)
                batch = _entradas(root)
                batch, frontera = _filtrar_por_fecha(batch, date_field, desde, hasta)
                all_records.extend(batch)
                logger.info(f"  página {page} — {len(batch)} entradas (total: {len(all_records)})")
                page += 1
                if preview_limit and len(all_records) >= preview_limit:
                    break
                if frontera:
                    logger.info("  frontera de fecha alcanzada; se detiene la paginación")
                    break
                if max_pages and page >= max_pages:
                    break
                next_url = _next_link(root)
                if next_url and delay:
                    time.sleep(delay)
            return all_records[:preview_limit] if preview_limit else all_records

        start = 0
        while True:
            query = {
                **fixed_params,
                start_param: str(start),
                page_size_param: str(effective_page_size),
            }

            response = self._request(session, method, url, params=query, headers=headers, timeout=timeout)
            response.raise_for_status()

            if not response.text or not response.text.strip():
                raise ValueError(f"Respuesta vacía del feed en offset {start}")

            try:
                root = ET.fromstring(response.text)
            except ET.ParseError as e:
                raise ValueError(f"No se pudo parsear el XML del feed: {e}\nRespuesta: {response.text[:200]}")

            entries = _entradas(root)
            raw_count = len(entries)
            entries, frontera = _filtrar_por_fecha(entries, date_field, desde)
            batch_count = len(entries)
            all_records.extend(entries)

            logger.info(f"  offset={start} — {batch_count} entradas (total: {len(all_records)})")

            page += 1

            if preview_limit and len(all_records) >= preview_limit:
                break

            if frontera:
                logger.info("  frontera de fecha alcanzada; se detiene la paginación")
                break

            if raw_count < effective_page_size:
                break

            if max_pages and page >= max_pages:
                logger.warning(f"Límite de páginas alcanzado: {max_pages}")
                break

            start += effective_page_size

        return all_records

    def parse(self, raw: RawData) -> ParsedData:
        return raw

    def normalize(self, parsed: ParsedData) -> DomainData:
        return parsed
