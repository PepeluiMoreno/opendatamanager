"""
FileDownloadFetcher — Descarga un fichero desde una URL y convierte cada fila en un dict.

Soporta los formatos más habituales en fuentes de datos abiertos:
    xlsx   — Excel (openpyxl)
    csv    — CSV estándar (auto-detect delimitador)
    tsv    — TSV (tab-separated, alias de csv con delimiter=\\t)

Params configurables (ResourceParam):
    url          URL directa al fichero          (obligatorio)
    format       Formato del fichero: xlsx | csv | tsv  (obligatorio)
    sheet        Hoja XLSX: nombre o índice 0-based (default: 0, solo xlsx)
    skip_rows    Filas a saltar antes de la cabecera (default: 0)
    delimiter    Separador CSV/TSV (default: auto-detect entre , ; \\t)
    encoding     Codificación CSV/TSV (default: utf-8-sig, tolera BOM)
    timeout      Timeout HTTP en segundos (default: 60)
    headers      Headers HTTP adicionales como JSON string
    batch_size   Registros por chunk yield (default: 1000)

Flujo:
    1. GET → fichero en memoria (BytesIO / StringIO, sin tocar disco).
    2. Parse con pandas (xlsx) o csv stdlib (csv/tsv).
    3. Normalizar columnas: strip → lowercase → espacios/guiones → _ → quitar no-ASCII.
    4. Yield en batches de batch_size registros como List[Dict[str, str]].

Extensibilidad:
    Para añadir un nuevo formato (json_lines, parquet, xml…) basta con añadir
    un método _parse_<format> y registrarlo en el dispatcher _PARSERS.
"""

import io
import re
import csv
import json
import logging
import requests
import pandas as pd
from typing import Generator, List, Dict, Any, Callable
from app.fetchers.base import BaseFetcher, RawData, ParsedData, DomainData

logger = logging.getLogger(__name__)

# Mapa de caracteres acentuados → ASCII para normalizar nombres de columna
_ACCENT_MAP = str.maketrans(
    "áéíóúÁÉÍÓÚñÑüÜ",
    "aeiouAEIOUnNuU",
)


def _normalize_col(name: str) -> str:
    """Convierte un nombre de columna a snake_case ASCII limpio."""
    name = str(name).translate(_ACCENT_MAP)
    name = name.strip().lower()
    name = re.sub(r"[\s\-/\\\.]+", "_", name)
    name = re.sub(r"[^\w]", "", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "col"


def _detect_delimiter(sample: str) -> str:
    """Detecta el delimitador más probable en las primeras líneas."""
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        return dialect.delimiter
    except csv.Error:
        return ";" if sample.count(";") >= sample.count(",") else ","


class FileDownloadFetcher(BaseFetcher):
    """
    Fetcher genérico para ficheros descargables (XLSX, CSV, TSV…).

    El formato se controla con el parámetro `format`.  El resto del pipeline
    (staging, dataset, notificaciones) es idéntico al de cualquier otro fetcher.
    """

    # ── Dispatchers de formato ─────────────────────────────────────────────

    def _parse_xlsx(self, content: bytes, params: dict) -> List[Dict[str, str]]:
        sheet = params.get("sheet", 0)
        try:
            sheet = int(sheet)
        except (ValueError, TypeError):
            pass

        skip_rows = int(params.get("skip_rows", 0))

        df = pd.read_excel(
            io.BytesIO(content),
            sheet_name=sheet,
            skiprows=skip_rows,
            dtype=str,
            engine="openpyxl",
        )
        df.columns = [_normalize_col(c) for c in df.columns]
        df = df.dropna(how="all").fillna("")
        logger.info(f"[FileDownloadFetcher] xlsx — {len(df)} filas, columnas: {list(df.columns)}")
        return df.to_dict(orient="records")

    def _parse_csv(self, content: bytes, params: dict, delimiter: str = "") -> List[Dict[str, str]]:
        encoding = params.get("encoding", "utf-8-sig")
        skip_rows = int(params.get("skip_rows", 0))

        # Columnas explícitas (para ficheros sin cabecera, e.g. Geonames TSV)
        # Si se proporcionan, la primera fila se trata como dato, no como cabecera.
        explicit_columns_raw = params.get("columns", "")
        if explicit_columns_raw:
            if isinstance(explicit_columns_raw, str):
                import json as _json
                explicit_columns = _json.loads(explicit_columns_raw)
            else:
                explicit_columns = list(explicit_columns_raw)
        else:
            explicit_columns = []

        text = content.decode(encoding, errors="replace")

        if not delimiter:
            delimiter = params.get("delimiter", "")
        if not delimiter:
            sample = "\n".join(text.splitlines()[:5])
            delimiter = _detect_delimiter(sample)
            logger.info(f"[FileDownloadFetcher] Delimitador detectado: {repr(delimiter)}")

        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        for _ in range(skip_rows):
            next(reader, None)

        if explicit_columns:
            columns = [_normalize_col(c) for c in explicit_columns]
            logger.info(f"[FileDownloadFetcher] csv (sin cabecera) — {len(columns)} columnas explícitas")
        else:
            raw_header = next(reader, None)
            if not raw_header:
                return []
            columns = [_normalize_col(c) for c in raw_header]
            logger.info(f"[FileDownloadFetcher] csv — {len(columns)} columnas: {columns}")

        records = []
        for row in reader:
            padded = row + [""] * max(0, len(columns) - len(row))
            records.append({col: padded[i].strip() for i, col in enumerate(columns)})
        return records

    # ── Dispatcher principal ───────────────────────────────────────────────

    _FORMAT_ALIASES = {"tsv": ("csv", "\t")}

    def _parse(self, content: bytes, fmt: str) -> List[Dict[str, str]]:
        if fmt in self._FORMAT_ALIASES:
            base_fmt, forced_delim = self._FORMAT_ALIASES[fmt]
            return self._parse_csv(content, self.params, delimiter=forced_delim)
        if fmt == "xlsx":
            return self._parse_xlsx(content, self.params)
        if fmt == "csv":
            return self._parse_csv(content, self.params)
        raise ValueError(
            f"Formato '{fmt}' no soportado. Valores válidos: xlsx, csv, tsv"
        )

    # ── Interfaz BaseFetcher ───────────────────────────────────────────────

    def stream(self) -> Generator[List[Dict[str, Any]], None, None]:
        url = self.params.get("url")
        if not url:
            raise ValueError("El parámetro 'url' es obligatorio para FileDownloadFetcher")

        fmt = self.params.get("format", "").lower().strip()
        if not fmt:
            # Infer from URL extension as fallback
            for ext in ("xlsx", "csv", "tsv"):
                if url.lower().endswith(f".{ext}") or f".{ext}?" in url.lower():
                    fmt = ext
                    break
        if not fmt:
            raise ValueError(
                "El parámetro 'format' es obligatorio. Valores válidos: xlsx, csv, tsv"
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

        records = self._parse(response.content, fmt)
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
