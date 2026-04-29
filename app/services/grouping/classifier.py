"""Clasificador de segmentos de path en dimensiones tipadas."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional, Tuple


_CURRENT_YEAR = datetime.utcnow().year

_YEAR_RE = re.compile(r"^(?:19|20)\d{2}$")
_MONTH_NUM_RE = re.compile(r"^(?:0?[1-9]|1[0-2])$")
_MONTH_NAMES_ES = {
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "setiembre", "octubre", "noviembre", "diciembre",
}
_MONTH_NAMES_EN = {
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
}
_QUARTER_RE = re.compile(r"^(?:[Tt][1-4]|[Qq][1-4]|[1-4][Tt])$")
_DATE_FULL_RE = re.compile(r"^\d{4}[-_]?\d{2}[-_]?\d{2}$")
FILENAME_YEAR_RE = re.compile(r"(?<![0-9])(?:19|20)\d{2}(?![0-9])")


def classify_segment(seg: str) -> Tuple[Optional[str], str]:
    """Devuelve (kind, value_normalized) o (None, seg) si no encaja en una dimensión tipada."""
    if not seg:
        return None, seg
    sl = seg.lower()
    if _YEAR_RE.fullmatch(seg):
        try:
            v = int(seg)
            if 1990 <= v <= _CURRENT_YEAR + 1:
                return "year", seg
        except ValueError:
            pass
    if sl in _MONTH_NAMES_ES or sl in _MONTH_NAMES_EN:
        return "month", sl
    if _MONTH_NUM_RE.fullmatch(seg):
        return "month", seg.zfill(2)
    if _QUARTER_RE.fullmatch(seg):
        return "quarter", seg.upper()
    if _DATE_FULL_RE.fullmatch(seg):
        return "date", seg
    return None, seg


def classify_year_in_filename(filename: str) -> Optional[str]:
    """Extrae el primer año plausible del nombre de fichero, o None."""
    m = FILENAME_YEAR_RE.search(filename)
    if not m:
        return None
    try:
        v = int(m.group(0))
    except ValueError:
        return None
    if not (1990 <= v <= _CURRENT_YEAR + 1):
        return None
    return str(v)
