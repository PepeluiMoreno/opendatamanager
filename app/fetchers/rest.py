import requests
import json
import time
from app.fetchers.base import BaseFetcher, RawData, ParsedData, DomainData
from app.fetchers.pagination import build as build_pagination
from app.fetchers.request_building import build_request


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
    if content_field:
        val = _dig(data, content_field)
        return val if isinstance(val, list) else []
    return data if isinstance(data, list) else []


class RESTFetcher(BaseFetcher):
    """Fetcher genérico para APIs REST/JSON sobre HTTP — la ESPECIE REST.

    Las peculiaridades se delegan en categorías de variación con registro propio:
      - construcción de la petición (`request`): query | json_body | form | graphql | sparql
      - paginación (`pagination`): none | query_offset | page_number | rel_next | cursor | pivot_loop
      - extracción (`extraction`): passthrough | field_map | timeseries_long | bindings
    Por defecto (request=query, pagination=none, extraction=passthrough) hace una
    sola petición GET y devuelve el JSON tal cual: comportamiento histórico.
    """

    def fetch(self) -> RawData:
        url = self.params.get("url")
        if not url:
            raise ValueError("El parámetro 'url' es obligatorio para RESTFetcher")
        timeout = int(self.params.get("timeout", 30))

        headers = self.params.get("headers", {})
        if isinstance(headers, str):
            headers = json.loads(headers) if headers.strip() else {}
        query_params = self.params.get("query_params", {})
        if isinstance(query_params, str):
            query_params = json.loads(query_params) if query_params.strip() else {}

        request_strategy = self.params.get("request", "query")
        pagination = (self.params.get("pagination") or "none").lower()

        def _send(target_url, extra_query, pivot=None):
            rq = build_request(request_strategy, self.params, pivot=pivot)
            merged_headers = {**headers, **rq.get("headers", {})}
            q = {**query_params, **(extra_query or {})}
            kwargs = {"headers": merged_headers, "params": q, "timeout": timeout}
            if rq.get("json") is not None:
                kwargs["json"] = rq["json"]
            if rq.get("data") is not None:
                kwargs["data"] = rq["data"]
            resp = self._request(None, rq["method"], target_url, **kwargs)
            resp.raise_for_status()
            return resp

        # Modo histórico: una sola petición, cuerpo según la estrategia, JSON sin tocar.
        if pagination in ("", "none"):
            return _send(url, {}).text

        # Modo paginado: recorre con la estrategia y acumula registros.
        content_field = self.params.get("content_field")
        next_link_field = self.params.get("next_link_field")
        cursor_field = self.params.get("cursor_field")
        max_records = int(self.params.get("max_records", 0) or 0)
        delay = float(self.params.get("delay", self.params.get("delay_between_pages", 0)) or 0)
        preview_limit = int(self.params.get("_preview_limit", 0) or 0)

        strat = build_pagination(pagination, url, self.params)
        spec = strat.first()
        all_records = []
        while spec:
            resp = _send(spec["url"], spec.get("query"), pivot=spec.get("pivot"))
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
        if isinstance(raw, (list, dict)):
            return raw
        if not raw or not raw.strip():
            raise ValueError("La respuesta del servidor está vacía (body vacío)")
        return json.loads(raw)

    def normalize(self, parsed: ParsedData) -> DomainData:
        extraction = self.params.get("extraction")
        if extraction:
            from app.fetchers.extraction import extract
            return extract(extraction, parsed, self.params)
        return parsed


RestFetcher = RESTFetcher
