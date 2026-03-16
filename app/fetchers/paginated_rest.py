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
from typing import List, Dict, Any
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

    def fetch(self) -> RawData:
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

        # Params fijos adicionales
        fixed_params = self.params.get("query_params", {})
        if isinstance(fixed_params, str):
            fixed_params = json.loads(fixed_params)

        # Headers adicionales
        headers = self.params.get("headers", {})
        if isinstance(headers, str):
            headers = json.loads(headers)

        preview_limit = int(self.params.get("_preview_limit", 0))

        # En modo preview usamos el límite como page_size para no pedir más de lo necesario
        effective_page_size = min(page_size, preview_limit) if preview_limit else page_size

        all_records: List[Dict[str, Any]] = []
        seen_ids = set()
        page = 0
        total_pages_fetched = 0

        logger.info(f"Iniciando fetch paginado: {url} (page_size={effective_page_size})"
                    + (f" [preview_limit={preview_limit}]" if preview_limit else ""))

        session = requests.Session()

        while True:
            query = {**fixed_params, page_param: str(page), page_size_param: str(effective_page_size)}

            logger.info(f"  Página {page} — registros acumulados: {len(all_records)}")

            response = session.request(method, url, params=query, headers=headers, timeout=timeout)
            response.raise_for_status()

            if not response.text or not response.text.strip():
                raise ValueError(f"La API devolvió respuesta vacía en página {page}")

            data = json.loads(response.text)

            # Extraer registros del campo configurado
            content = data.get(content_field, [])
            if not isinstance(content, list):
                raise ValueError(
                    f"El campo '{content_field}' no es una lista. "
                    f"Respuesta: {str(data)[:200]}"
                )

            batch_count = 0
            for record in content:
                if id_field:
                    record_id = str(record.get(id_field, ""))
                    if record_id and record_id in seen_ids:
                        continue
                    if record_id:
                        seen_ids.add(record_id)

                all_records.append(record)
                batch_count += 1

            total_pages_fetched += 1

            # En modo preview, parar en cuanto tengamos suficientes registros
            if preview_limit and len(all_records) >= preview_limit:
                logger.info(f"  Preview limit alcanzado: {len(all_records)} registros")
                break

            # Condición de fin: página incompleta = última página
            if batch_count < effective_page_size:
                logger.info(f"  Última página alcanzada (batch={batch_count} < page_size={page_size})")
                break

            # Límite de seguridad
            if max_pages and total_pages_fetched >= max_pages:
                logger.warning(f"  Límite de seguridad alcanzado: {max_pages} páginas")
                break

            page += 1

            if delay > 0:
                time.sleep(delay)

        logger.info(f"Fetch completado: {len(all_records)} registros en {total_pages_fetched} páginas")
        return all_records

    def parse(self, raw: RawData) -> ParsedData:
        # Los datos ya vienen como lista de dicts desde fetch()
        return raw

    def normalize(self, parsed: ParsedData) -> DomainData:
        return parsed
