"""Sustitución de segmentos-dimensión por placeholders → path_template."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .classifier import classify_segment, _CURRENT_YEAR


def template_path_segments(segments: List[str]) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Templatea cada segmento; devuelve (template_segs, dimensiones detectadas con su valor)."""
    template: List[str] = []
    dims: List[Dict[str, Any]] = []
    for i, seg in enumerate(segments):
        kind, value = classify_segment(seg)
        if kind:
            template.append("{" + kind + "}")
            dims.append({
                "name": kind, "kind": kind, "segment_index": i,
                "in_filename": False, "value": value,
            })
        else:
            template.append(seg)
    return template, dims


# Patrones compuestos para detectar dimensiones DENTRO del filename.
# Se aplican en orden de prioridad — el más específico (year+month) primero —
# para evitar que el patrón de year-solo "consuma" un año que pertenece a un par.
#
# Notas:
#   - YYYY se valida posteriormente (rango 1990 .. _CURRENT_YEAR+1).
#   - MM exige zero-pad (0[1-9]|1[0-2]) — sin esto los digitos sueltos en filenames
#     como "Informe_Ta_Ley_15_10-2024.pdf" producirían falsos positivos.
#   - Quarter acepta T1..T4 y ordinales españoles 1oT..4oT.

_FILENAME_YEAR_MONTH_RE = re.compile(
    r"(?<![0-9])((?:19|20)\d{2})([-_])(0[1-9]|1[0-2])(?![0-9A-Za-z])"
)
_FILENAME_YEAR_QUARTER_T_RE = re.compile(
    r"(?<![0-9])((?:19|20)\d{2})([-_])([Tt][1-4])(?![0-9A-Za-z])"
)
_FILENAME_YEAR_QUARTER_OT_RE = re.compile(
    r"(?<![0-9])((?:19|20)\d{2})([-_])([1-4])([oO][TtQq])(?![0-9A-Za-z])"
)
_FILENAME_YEAR_ALONE_RE = re.compile(
    r"(?<![0-9])((?:19|20)\d{2})(?![0-9])"
)


def _valid_year(s: str) -> bool:
    try:
        v = int(s)
    except ValueError:
        return False
    return 1990 <= v <= _CURRENT_YEAR + 1


def _make_dim(name: str, value: str, segment_index: int) -> Dict[str, Any]:
    return {
        "name": name, "kind": name, "segment_index": segment_index,
        "in_filename": True, "value": value,
    }


def template_filename(
    filename: str, segment_index: int,
) -> Tuple[str, List[Dict[str, Any]]]:
    """Detecta dimensiones temporales dentro del filename y devuelve (template, dims).

    Prioridad: year+month > year+quarter (T) > year+ordinal_quarter > year solo.
    Sólo se aplica un patrón por filename.
    """
    # year + month: "2024_01"
    m = _FILENAME_YEAR_MONTH_RE.search(filename)
    if m and _valid_year(m.group(1)):
        sep = m.group(2)
        templated = filename[: m.start()] + "{year}" + sep + "{month}" + filename[m.end():]
        return templated, [
            _make_dim("year", m.group(1), segment_index),
            _make_dim("month", m.group(3), segment_index),
        ]

    # year + quarter T#: "2024-T1"
    m = _FILENAME_YEAR_QUARTER_T_RE.search(filename)
    if m and _valid_year(m.group(1)):
        sep = m.group(2)
        templated = filename[: m.start()] + "{year}" + sep + "{quarter}" + filename[m.end():]
        return templated, [
            _make_dim("year", m.group(1), segment_index),
            _make_dim("quarter", m.group(3).upper(), segment_index),
        ]

    # year + ordinal quarter "1oT": "2024-1oT"
    m = _FILENAME_YEAR_QUARTER_OT_RE.search(filename)
    if m and _valid_year(m.group(1)):
        sep = m.group(2)
        # Conservamos el sufijo "oT" en el template para no perder información de formato
        ordinal_suffix = m.group(4)
        templated = (
            filename[: m.start()] + "{year}" + sep + "{quarter}" + ordinal_suffix
            + filename[m.end():]
        )
        return templated, [
            _make_dim("year", m.group(1), segment_index),
            _make_dim("quarter", "T" + m.group(3), segment_index),
        ]

    # year solo
    m = _FILENAME_YEAR_ALONE_RE.search(filename)
    if m and _valid_year(m.group(1)):
        templated = filename[: m.start()] + "{year}" + filename[m.end():]
        return templated, [_make_dim("year", m.group(1), segment_index)]

    return filename, []


def humanize(token: str) -> str:
    return token.replace("-", " ").replace("_", " ").strip()
