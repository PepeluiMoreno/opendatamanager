import requests
import json
from app.fetchers.base import BaseFetcher, RawData, ParsedData, DomainData
from app.fetchers.pagination import build as build_pagination


def _dig(obj, path):
    """Navega un dict por una ruta con puntos. None si no existe."""
    if not path:
        return obj
    cur = obj
    for key in str(path).split("."):
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return None
    return cur


def _extract_list(data, content_field):
    """Saca la lista de registros de una página JSON.
    - content_field: ruta a la lista (p. ej. 'content' o 'data.items').
    - sin content_field: si la página YA es una lista, se usa; si no, [].
    """
    if content_field:
        val = _dig(data, content_field)
        return val if isinstance(val, list) else []
    return data if isinstance(data, list) else []


class RESTFetcher(BaseFetcher):
    """Fetcher genérico para APIs REST/JSON sobre HTTP.

    Es la ESPECIE REST: el recorrido del conjunto se delega en la categoría
    'paginación' (registro de estrategias). Sin `pagination` (o `none`) hace una
    única petición y devuelve el JSON tal cual (comportamiento histórico). Con
    una estrategia (`query_offset`, `page_number`, `rel_next`, `cursor`,
    `pivot_loop`) recorre las páginas y acumula los registros de `content_field`.
    """

    def fetch(self) -> RawData:
        url = self.params.get("url")
        if not url:
            raise ValueError("El parámetro 'url' es obligatorio para RESTFetcher")
        method = self.params.get("method", "GET").upper()
        timeout = int(self.params.get("timeout", 30))

        headers = self.params.get("headers", {})
        if isinstance(headers, str):
            headers = json.loads(headers) if headers.strip() else {}
        query_params = self.params.get("query_params", {})
        if isinstance(query_params, str):
            query_params = json.loads(query_params) if query_params.strip() else {}

        pagination = (self.params.get("pagination") or "none").lower()

        # Modo histórico: una sola petición, JSON sin tocar.
        if pagination in ("", "none"):
            response = self._request(None, method, url, headers=headers, params=query_params, timeout=timeout)
            response.raise_for_status()
            return response.text

        # Modo paginado: recorre con la estrategia y acumula registros.
        content_field = self.params.get("content_field")
        next_link_field = self.params.get("next_link_field")   # rel_next en JSON
        cursor_field = self.params.get("cursor_field")          # cursor
        max_records = int(self.params.get("max_records", 0) or 0)
        import time
        delay = float(self.params.get("delay", self.params.get("delay_between_pages", 0)) or 0)
        preview_limit = int(self.params.get("_preview_limit", 0) or 0)

        strat = build_pagination(pagination, url, self.params)
        spec = strat.first()
        all_records = []
        while spec:
            q = {**query_params, **(spec.get("query") or {})}
            resp = self._request(None, method, spec["url"], headers=headers, params=q, timeout=timeout)
            resp.raise_for_status()
            data = json.loads(resp.text) if resp.text and resp.text.strip() else {}
            batch = _extract_list(data, content_field)
            all_records.extend(batch)
            if preview_limit and len(all_records) >= preview_limit:
                break
            if max_records and len(all_records) >= max_records:
                break
            meta = {
                "next_link": _dig(data, next_link_field) if next_link_field else None,
                "next_cursor": _dig(data, cursor_field) if cursor_field else None,
            }
            nxt = strat.following(last_batch_size=len(batch), meta=meta)
            if nxt and delay:
                time.sleep(delay)
            spec = nxt
        return all_records[:preview_limit] if preview_limit else all_records

    def parse(self, raw: RawData) -> ParsedData:
        # En modo paginado, fetch() ya devuelve la lista de registros.
        if isinstance(raw, (list, dict)):
            return raw
        if not raw or not raw.strip():
            raise ValueError("La respuesta del servidor está vacía (body vacío)")
        return json.loads(raw)

    def normalize(self, parsed: ParsedData) -> DomainData:
        # Categoría 'extracción': si se indica una estrategia, se aplica; si no,
        # se devuelve el parseado tal cual (comportamiento histórico).
        extraction = self.params.get("extraction")
        if extraction:
            from app.fetchers.extraction import extract
            return extract(extraction, parsed, self.params)
        return parsed


# Alias para compatibilidad con nombres en base de datos
RestFetcher = RESTFetcher
