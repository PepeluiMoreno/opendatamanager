"""
FileDownloadFetcher — Descarga un fichero desde una URL y convierte sus filas en registros.
"""

import json
import logging
from typing import Generator, List, Dict, Any

from app.fetchers.base import BaseFetcher, RawData, ParsedData, DomainData
from app.fetchers.file_parsers import infer_file_format, parse_structured_file

logger = logging.getLogger(__name__)

class FileDownloadFetcher(BaseFetcher):
    def stream(self) -> Generator[List[Dict[str, Any]], None, None]:
        url = self.params.get("url")
        if not url:
            raise ValueError("El parámetro 'url' es obligatorio para FileDownloadFetcher")

        fmt = self.params.get("format", "").lower().strip()
        if not fmt:
            fmt = infer_file_format(url)
        if not fmt:
            raise ValueError(
                "El parámetro 'format' es obligatorio. Valores válidos: pdf, xls, xlsx, csv, tsv"
            )

        timeout = int(self.params.get("timeout", 60))
        batch_size = int(self.params.get("batch_size", 1000))

        http_headers = self.params.get("headers", {})
        if isinstance(http_headers, str):
            http_headers = json.loads(http_headers)

        logger.info(f"[FileDownloadFetcher] Descargando {fmt.upper()}: {url}")
        response = self._request(None, "GET", url, headers=http_headers, timeout=timeout)
        response.raise_for_status()
        logger.info(f"[FileDownloadFetcher] Descargado — {len(response.content):,} bytes")

        records = parse_structured_file(response.content, fmt, self.params, source_name=url)
        total = len(records)

        for start in range(0, total, batch_size):
            yield records[start:start + batch_size]

        logger.info(f"[FileDownloadFetcher] Stream completado: {total} registros")

    def fetch(self) -> RawData:
        records = []
        for chunk in self.stream():
            records.extend(chunk)
        return records

    def parse(self, raw: RawData) -> ParsedData:
        return raw

    def normalize(self, parsed: ParsedData) -> DomainData:
        return parsed
