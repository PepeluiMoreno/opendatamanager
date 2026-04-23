"""
PdfTableFetcher — Descarga un PDF desde una URL parametrizada e itera sobre años/meses/trimestres,
extrayendo la primera tabla de cada PDF con pdfplumber.

Emite una fila de dict por cada fila de la tabla, enriquecida con los campos
de periodo que se usaron para construir la URL (year, month, quarter).

Params configurables (ResourceParam):
    url_template   — URL con placeholders {year}, {month}, {quarter}   (obligatorio)
    year_from      — Primer año a procesar                              (obligatorio)
    year_to        — Último año a procesar                             (obligatorio)
    granularity    — 'monthly' | 'quarterly' | 'annual'                (obligatorio)
    table_index    — Índice de la tabla a extraer (0-based, default 0)
    header_row     — Índice de la fila de cabeceras dentro de la tabla (default 0)
    batch_size     — Registros por chunk yield (default 500)
    timeout        — Timeout HTTP por petición en segundos (default 30)

Flujo:
    1. Itera cada combinación (year, mes/trimestre) según granularity.
    2. Construye la URL sustituyendo placeholders en url_template.
    3. GET → PDF en memoria (BytesIO, sin tocar disco).
    4. pdfplumber extrae la tabla indicada por table_index.
    5. La fila header_row se usa como cabecera; se normaliza a snake_case ASCII.
    6. Añade campos _year, _month/_quarter según granularity.
    7. Yield en batches.
"""

import logging
from typing import Generator, List, Dict, Any

from app.fetchers.base import BaseFetcher, RawData, ParsedData, DomainData
from app.fetchers.file_parsers import parse_pdf_table

logger = logging.getLogger(__name__)


class PdfTableFetcher(BaseFetcher):
    """
    Fetcher que itera sobre un rango de años/meses/trimestres descargando un PDF
    por cada combinación y extrayendo su primera tabla con pdfplumber.
    """

    def stream(self) -> Generator[List[Dict[str, Any]], None, None]:
        url_template = self.params.get("url_template")
        if not url_template:
            raise ValueError("El parámetro 'url_template' es obligatorio para PdfTableFetcher")

        year_from = int(self.params.get("year_from", 0))
        year_to   = int(self.params.get("year_to", 0))
        if not year_from or not year_to:
            raise ValueError("Los parámetros 'year_from' y 'year_to' son obligatorios")

        granularity = self.params.get("granularity", "annual").lower()
        table_index = int(self.params.get("table_index", 0))
        header_row  = int(self.params.get("header_row", 0))
        batch_size  = int(self.params.get("batch_size", 500))
        timeout     = int(self.params.get("timeout", 30))

        buffer: List[Dict[str, Any]] = []

        for year in range(year_from, year_to + 1):
            if granularity == "monthly":
                periods = [{"month": m, "quarter": None} for m in range(1, 13)]
            elif granularity == "quarterly":
                periods = [{"month": None, "quarter": q} for q in range(1, 5)]
            else:
                periods = [{"month": None, "quarter": None}]

            for period in periods:
                month   = period["month"]
                quarter = period["quarter"]

                url = url_template.format(
                    year=year,
                    month=f"{month:02d}" if month else "",
                    quarter=quarter or "",
                )

                logger.info(f"[PdfTableFetcher] Descargando: {url}")
                try:
                    response = self._request(None, "GET", url, timeout=timeout)
                except Exception as exc:
                    logger.warning(f"[PdfTableFetcher] Error descargando {url}: {exc} — saltando")
                    continue

                records = parse_pdf_table(
                    response.content,
                    {"table_index": table_index, "header_row": header_row},
                )
                if not records:
                    logger.info(f"[PdfTableFetcher] Sin tabla en {url}")
                    continue

                # Enriquecer con metadatos de periodo
                for rec in records:
                    rec["_year"] = str(year)
                    if month is not None:
                        rec["_month"] = f"{month:02d}"
                    if quarter is not None:
                        rec["_quarter"] = f"T{quarter}"

                buffer.extend(records)
                logger.info(
                    f"[PdfTableFetcher] {url} → {len(records)} filas "
                    f"(buffer acumulado: {len(buffer)})"
                )

                while len(buffer) >= batch_size:
                    yield buffer[:batch_size]
                    buffer = buffer[batch_size:]

                # Actualizar resume state para soporte pause/resume
                self.current_state = {
                    "last_year": year,
                    "last_month": month,
                    "last_quarter": quarter,
                }

        if buffer:
            yield buffer

    def fetch(self) -> RawData:
        records = []
        for chunk in self.stream():
            records.extend(chunk)
        return records

    def parse(self, raw: RawData) -> ParsedData:
        return raw

    def normalize(self, parsed: ParsedData) -> DomainData:
        return parsed
