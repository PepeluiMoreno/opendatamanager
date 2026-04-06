"""
PaginatedRestFetcher - Fetcher para APIs REST JSON con paginación por offset.

Estrategia idéntica a bdns_etl:
- Itera páginas 0, 1, 2... hasta que content.length < page_size
- Extrae registros del campo configurable (por defecto "content")
- Deduplica por campo id configurable
- No carga todo en RAM: acumula lista pero escribe en JSONL línea a línea
  cuando se usa desde FetcherManager
"""
import json
import time
import logging
import requests
from typing import Generator, List, Dict, Any
from app.fetchers.base import BaseFetcher, RawData, ParsedData, DomainData

logger = logging.getLogger(__name__)


class PaginatedRestFetcher(BaseFetcher):
    """
    Fetcher para APIs REST paginadas que devuelven JSON con estructura:
    {
        "content": [...],
        "totalPages": N,
        "last": true/false,
        ...
    }

    Params configurables via ResourceParam:
        url               URL base del endpoint (obligatorio)
        method            Método HTTP (default: get)
        page_size         Registros por página (default: 10000)
        page_size_param   Nombre del param de pageSize en la API (default: pageSize)
        page_param        Nombre del param de página en la API (default: page)
        content_field     Campo JSON que contiene los registros (default: content)
        id_field          Campo para deduplicación (default: id, vacío = sin dedup)
        max_pages         Límite de seguridad de páginas (default: 0 = sin límite)
        delay_between_pages  Segundos entre peticiones (default: 0)
        query_params      Params fijos adicionales como JSON string
        headers           Headers adicionales como JSON string
        timeout           Timeout en segundos (default: 60)
    """

    def _build_request_config(self):
        """Returns (url, method, page_size, effective_page_size, fixed_params, headers,
        page_param, page_size_param, content_field, id_field, max_pages, delay, timeout,
        preview_limit) from self.params."""
        url = self.params.get("url")
        if not url:
            raise ValueError("El parámetro 'url' es obligatorio para PaginatedRestFetcher")

        method = self.params.get("method", "get").upper()
        page_size = int(self.params.get("page_size", 10000))
        page_size_param = self.params.get("page_size_param", "pageSize")
        page_param = self.params.get("page_param", "page")
        content_field = self.params.get("content_field", "content")
        id_field = self.params.get("id_field", "id")
        max_pages = int(self.params.get("max_pages", 0))
        delay = float(self.params.get("delay_between_pages", 0))
        timeout = int(self.params.get("timeout", 60))

        fixed_params = self.params.get("query_params", {})
        if isinstance(fixed_params, str):
            fixed_params = json.loads(fixed_params)

        _control_keys = {
            "url", "method", "page_size", "page_size_param", "page_param",
            "content_field", "id_field", "max_pages", "delay_between_pages",
            "query_params", "headers", "timeout", "_preview_limit",
            "bounding_field", "bounding_value", "page_start",
        }
        for key, value in self.params.items():
            if key not in _control_keys and value not in (None, ""):
                fixed_params.setdefault(key, str(value))

        headers = self.params.get("headers", {})
        if isinstance(headers, str):
            headers = json.loads(headers)

        preview_limit = int(self.params.get("_preview_limit", 0))
        effective_page_size = min(page_size, preview_limit) if preview_limit else page_size

        return (url, method, page_size, effective_page_size, fixed_params, headers,
                page_param, page_size_param, content_field, id_field, max_pages, delay,
                timeout, preview_limit)

    def stream(self) -> Generator[List[Dict[str, Any]], None, None]:
        """Yields one page of records at a time — no full accumulation in RAM."""
        (url, method, page_size, effective_page_size, fixed_params, headers,
         page_param, page_size_param, content_field, id_field, max_pages, delay,
         timeout, preview_limit) = self._build_request_config()

        filter_lte_field = self.params.get("bounding_field", "")
        _filter_lte_raw = self.params.get("bounding_value", "")
        filter_lte_value = int(_filter_lte_raw) if _filter_lte_raw else None

        # Resume protocol: restore page number from saved state
        resume_state = self.params.get("_resume_state") or {}
        if isinstance(resume_state, str):
            resume_state = json.loads(resume_state)
        default_page = int(self.params.get("page_start", 0))
        start_page = int(resume_state.get("page", default_page))

        seen_ids: set = set()
        page = start_page
        total_pages_fetched = 0
        total_yielded = 0

        if start_page:
            logger.info(f"Resuming from page {start_page}")
        logger.info(f"Iniciando fetch paginado (streaming): {url} (page_size={effective_page_size})"
                    + (f" [preview_limit={preview_limit}]" if preview_limit else ""))

        http = requests.Session()

        while True:
            query = {**fixed_params, page_param: str(page), page_size_param: str(effective_page_size)}
            logger.info(f"  Página {page} — registros hasta ahora: {total_yielded}")

            response = self._request(http, method, url,
                                      params=query, headers=headers, timeout=timeout)

            if not response.text or not response.text.strip():
                raise ValueError(f"La API devolvió respuesta vacía en página {page}")

            data = json.loads(response.text)
            if isinstance(data, list):
                # API returns a top-level array directly
                content = data
            else:
                content = data.get(content_field, [])
            if not isinstance(content, list):
                raise ValueError(
                    f"El campo '{content_field}' no es una lista. "
                    f"Respuesta: {str(data)[:200]}"
                )

            page_records: List[Dict[str, Any]] = []
            for record in content:
                if id_field:
                    record_id = str(record.get(id_field, ""))
                    if record_id and record_id in seen_ids:
                        continue
                    if record_id:
                        seen_ids.add(record_id)
                if filter_lte_field and filter_lte_value is not None:
                    try:
                        if int(record.get(filter_lte_field, 0)) > filter_lte_value:
                            continue
                    except (TypeError, ValueError):
                        pass
                page_records.append(record)

            batch_count = len(page_records)
            total_pages_fetched += 1

            if page_records:
                # Set savepoint BEFORE yield — if FetcherManager breaks at yield,
                # code after yield won't run. Next page to fetch = page + 1.
                self.current_state = {"page": page + 1}
                yield page_records
            total_yielded += batch_count

            if preview_limit and total_yielded >= preview_limit:
                logger.info(f"  Preview limit alcanzado: {total_yielded} registros")
                break

            if batch_count < effective_page_size:
                logger.info(f"  Última página alcanzada (batch={batch_count} < page_size={page_size})")
                break

            if max_pages and total_pages_fetched >= max_pages:
                logger.warning(f"  Límite de seguridad alcanzado: {max_pages} páginas")
                break

            page += 1
            if delay > 0:
                time.sleep(delay)

        logger.info(f"Stream completado: {total_yielded} registros en {total_pages_fetched} páginas")

    def fetch(self) -> RawData:
        """Accumulates all pages — used for preview and backwards compat."""
        all_records: List[Dict[str, Any]] = []
        for chunk in self.stream():
            all_records.extend(chunk)
        logger.info(f"Fetch completado: {len(all_records)} registros totales")
        return all_records

    def parse(self, raw: RawData) -> ParsedData:
        return raw

    def normalize(self, parsed: ParsedData) -> DomainData:
        return parsed
