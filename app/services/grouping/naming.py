"""Generación de nombre legible a partir del path templatizado y las dimensiones."""

from __future__ import annotations

from typing import Any, Dict, List

from .templating import humanize


# Tokens que aparecen como carpetas administrativas en muchos CMS (TypO3, WordPress…)
# y no aportan al nombre del recurso. Se filtran del suggested_name; nunca del grouping.
_NOISE_NAME_SEGMENTS = {
    "transparencia", "fileadmin", "documentos", "infopublica",
    "content", "files", "docs", "public", "wp-content", "uploads",
    "media", "assets", "data", "datos",
}


def suggested_name(
    constant_path_segments: List[str],
    templated_filename: str,
    dims: List[Dict[str, Any]],
) -> str:
    """Construye un nombre legible humano para la propuesta."""
    parts: List[str] = []
    for seg in constant_path_segments:
        if seg.startswith("{") or not seg:
            continue
        if seg.lower() in _NOISE_NAME_SEGMENTS:
            continue
        parts.append(humanize(seg))
    base = templated_filename.rsplit(".", 1)[0] if "." in templated_filename else templated_filename
    if base and not base.startswith("{"):
        parts.append(humanize(base))
    if not parts:
        parts.append("recurso")
    name = " — ".join(p for p in parts if p)
    if name:
        name = name[0].upper() + name[1:]

    has_year = any(d["kind"] == "year" for d in dims)
    has_month = any(d["kind"] == "month" for d in dims)
    has_quarter = any(d["kind"] == "quarter" for d in dims)
    has_date = any(d["kind"] == "date" for d in dims)
    if has_date:
        name += " (por fecha)"
    elif has_year and has_month:
        name += " (mensual)"
    elif has_year and has_quarter:
        name += " (trimestral)"
    elif has_year:
        name += " (anual)"
    elif has_month:
        name += " (mensual)"
    elif has_quarter:
        name += " (trimestral)"
    return name
