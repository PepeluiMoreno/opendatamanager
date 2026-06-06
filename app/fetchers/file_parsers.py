"""
Helpers compartidos para parsear ficheros descargados por distintos fetchers.

Centraliza el soporte para formatos tabulares y PDF, además de una vía
controlada de parser especializado para artefactos especialmente raros.
"""

from __future__ import annotations

import csv
import importlib
import io
import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional

import pandas as pd
import pdfplumber

logger = logging.getLogger(__name__)

_ACCENT_MAP = str.maketrans(
    "áéíóúÁÉÍÓÚñÑüÜ",
    "aeiouAEIOUnNuU",
)

_EXT_TO_FORMAT = {
    ".csv": "csv",
    ".tsv": "tsv",
    ".txt": "tsv",
    ".xlsx": "xlsx",
    ".xls": "xls",
    ".pdf": "pdf",
}


_LEYENDA_RE = __import__("re").compile(
    r"\(?\s*[a-z]\s*\)?"                                   # ( a )
    r"|[a-z]\s*=\s*\(?[a-z0-9+\-*/() .,%]+\)?",            # c=a+b · o=(i+j+k)*100/c
    __import__("re").IGNORECASE,
)


def _es_fila_leyenda(celdas) -> bool:
    """Fila-leyenda de fórmulas bajo la cabecera (estados presupuestarios:
    '( a )', 'c=a+b'...): ≥2 celdas pobladas y TODAS con pinta de leyenda."""
    pobladas = [str(c).strip() for c in celdas if str(c).strip()]
    return len(pobladas) >= 2 and all(_LEYENDA_RE.fullmatch(c) for c in pobladas)


def _drop_empty_columns(registros):
    """Elimina columnas íntegramente vacías (márgenes fantasma de tablas PDF,
    columnas decorativas de Excel)."""
    if not registros:
        return registros
    vacias = {k for k in registros[0]
              if all(not str(r.get(k, "")).strip() for r in registros)}
    if not vacias:
        return registros
    return [{k: v for k, v in r.items() if k not in vacias} for r in registros]


def _normalize_col(name: str) -> str:
    """Convierte un nombre de columna a snake_case ASCII limpio."""
    name = str(name).translate(_ACCENT_MAP)
    name = name.strip().lower()
    name = re.sub(r"[\s\-/\\\.()]+", "_", name)
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


def infer_file_format(filename_or_url: str) -> str:
    lowered = (filename_or_url or "").lower()
    for ext, fmt in _EXT_TO_FORMAT.items():
        if lowered.endswith(ext) or f"{ext}?" in lowered:
            return fmt
    return ""


def _parse_json_if_needed(value: Any, default: Any) -> Any:
    if value in (None, ""):
        return default
    if isinstance(value, str):
        return json.loads(value)
    return value


def _load_custom_parser(parser_ref: str) -> Callable[..., List[Dict[str, Any]]]:
    if ":" in parser_ref:
        module_path, func_name = parser_ref.split(":", 1)
    else:
        module_path, func_name = parser_ref.rsplit(".", 1)
    module = importlib.import_module(module_path)
    fn = getattr(module, func_name, None)
    if fn is None or not callable(fn):
        raise ValueError(f"Custom parser '{parser_ref}' is not a callable")
    return fn


def _parse_excel(content: bytes, params: Dict[str, Any], fmt: str) -> List[Dict[str, str]]:
    sheet = params.get("sheet", 0)
    try:
        sheet = int(sheet)
    except (ValueError, TypeError):
        pass

    skip_rows = int(params.get("skip_rows", 0))
    engine = "xlrd" if fmt == "xls" else "openpyxl"
    fallback = "xlrd" if engine == "openpyxl" else "openpyxl"

    for eng in (engine, fallback):
        try:
            raw = pd.read_excel(
                io.BytesIO(content),
                sheet_name=sheet,
                skiprows=skip_rows,
                header=None,
                dtype=str,
                engine=eng,
            ).fillna("")
            rows = [[str(c).strip() for c in fila] for fila in raw.values.tolist()]
            hdr = _sniff_header_row(rows, params)
            cabecera = rows[hdr] if hdr < len(rows) else []
            columns = [_normalize_col(c) if c else f"col_{i}" for i, c in enumerate(cabecera)]
            registros = []
            for fila in rows[hdr + 1:]:
                if not any(c for c in fila):
                    continue
                if _es_fila_leyenda(fila):
                    continue
                registros.append({columns[i] if i < len(columns) else f"col_{i}": v
                                  for i, v in enumerate(fila)})
            return _drop_empty_columns(registros)
        except Exception:
            if eng == fallback:
                raise


def _sniff_header_row(rows, params) -> int:
    """Localiza la fila de cabecera de una hoja Excel.

    Los ficheros municipales suelen abrir con filas-pancarta (un título fusionado
    a lo ancho) antes de la cabecera real. Si el recurso fija `header_row`, manda;
    si no, se elige la primera fila de las ~15 iniciales con ≥2 celdas pobladas y
    una anchura cercana a la máxima observada (la pancarta de celda única nunca
    cumple)."""
    if "header_row" in params:
        try:
            return int(params["header_row"])
        except (TypeError, ValueError):
            pass
    ventana = rows[:15]
    anchos = [sum(1 for c in fila if c) for fila in ventana]
    if not anchos:
        return 0
    maximo = max(anchos)
    for i, n in enumerate(anchos):
        if n >= 2 and n >= 0.6 * maximo:
            return i
    return 0


def _parse_csv_like(content: bytes, params: Dict[str, Any], delimiter: str = "") -> List[Dict[str, str]]:
    encoding = params.get("encoding", "utf-8-sig")
    skip_rows = int(params.get("skip_rows", 0))

    explicit_columns_raw = params.get("columns", "")
    if explicit_columns_raw:
        explicit_columns = _parse_json_if_needed(explicit_columns_raw, [])
    else:
        explicit_columns = []

    text = content.decode(encoding, errors="replace")

    if not delimiter:
        delimiter = params.get("delimiter", "")
    if not delimiter:
        sample = "\n".join(text.splitlines()[:5])
        delimiter = _detect_delimiter(sample)

    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    for _ in range(skip_rows):
        next(reader, None)

    if explicit_columns:
        columns = [_normalize_col(c) for c in explicit_columns]
    else:
        raw_header = next(reader, None)
        if not raw_header:
            return []
        columns = [_normalize_col(c) for c in raw_header]

    records: List[Dict[str, str]] = []
    for row in reader:
        padded = row + [""] * max(0, len(columns) - len(row))
        records.append({col: padded[i].strip() for i, col in enumerate(columns)})
    return records


def parse_pdf_table(content: bytes, params: Dict[str, Any]) -> List[Dict[str, str]]:
    table_index = int(params.get("table_index", 0))
    header_row = int(params.get("header_row", 0))

    with pdfplumber.open(io.BytesIO(content)) as pdf:
        all_tables = []
        for page in pdf.pages:
            all_tables.extend(page.extract_tables())

    if not all_tables:
        return []

    if table_index >= len(all_tables):
        logger.warning(
            "[file_parsers] table_index=%s fuera de rango (%s tablas encontradas). Usando tabla 0.",
            table_index,
            len(all_tables),
        )
        table = all_tables[0]
    else:
        table = all_tables[table_index]

    if len(table) <= header_row:
        return []

    filas_norm = [[str(c or "").strip() for c in fila] for fila in table]
    if "header_row" not in params:
        header_row = _sniff_header_row(filas_norm, params)
    raw_headers = filas_norm[header_row]
    columns = [_normalize_col(h) if h else f"col_{i}" for i, h in enumerate(raw_headers)]

    records: List[Dict[str, str]] = []
    for row in filas_norm[header_row + 1:]:
        if _es_fila_leyenda(row):
            continue
        if not any(cell for cell in row if cell):
            continue
        padded = list(row) + [""] * max(0, len(columns) - len(row))
        records.append({col: str(padded[i] or "").strip() for i, col in enumerate(columns)})
    return _drop_empty_columns(records)


def parse_structured_file(
    content: bytes,
    fmt: str,
    params: Optional[Dict[str, Any]] = None,
    source_name: str = "",
) -> List[Dict[str, Any]]:
    params = params or {}
    fmt = (fmt or "").lower().strip()
    custom_parser = params.get("custom_parser")

    if custom_parser:
        fn = _load_custom_parser(custom_parser)
        return fn(content=content, params=params, source_name=source_name, format=fmt)

    if fmt == "xlsx":
        return _parse_excel(content, params, "xlsx")
    if fmt == "xls":
        return _parse_excel(content, params, "xls")
    if fmt == "csv":
        return _parse_csv_like(content, params)
    if fmt == "tsv":
        return _parse_csv_like(content, params, delimiter="\t")
    if fmt == "pdf":
        return parse_pdf_table(content, params)

    raise ValueError(
        f"Formato '{fmt}' no soportado. Valores válidos: pdf, xls, xlsx, csv, tsv"
    )
