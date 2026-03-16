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

        all_records: List[Dict[str, Any]] = []
        start = 0
        page = 0

        logger.info(f"Iniciando fetch ATOM: {url}")

        session = requests.Session()

        while True:
            query = {
                **fixed_params,
                start_param: str(start),
                page_size_param: str(effective_page_size),
            }

            response = session.request(method, url, params=query, headers=headers, timeout=timeout)
            response.raise_for_status()

            if not response.text or not response.text.strip():
                raise ValueError(f"Respuesta vacía del feed en offset {start}")

            try:
                root = ET.fromstring(response.text)
            except ET.ParseError as e:
                raise ValueError(f"No se pudo parsear el XML del feed: {e}\nRespuesta: {response.text[:200]}")

            entries = _parse_feed_entries(root)
            batch_count = len(entries)
            all_records.extend(entries)

            logger.info(f"  offset={start} — {batch_count} entradas (total: {len(all_records)})")

            page += 1

            if preview_limit and len(all_records) >= preview_limit:
                break

            if batch_count < effective_page_size:
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
