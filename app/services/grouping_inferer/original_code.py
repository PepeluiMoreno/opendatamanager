"""
Algoritmo original de inferencia de agrupaciones.

Este módulo es una migración directa del fichero plano
`app/services/grouping_inferer.py` anterior. No se modifica su lógica;
simplemente se reubica aquí para que GenericGroupingInferer lo envuelva
y para preservar la retrocompatibilidad de cualquier import directo.

Función principal: infer(leaf_urls) -> List[GroupingProposal]
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse


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
_FILENAME_YEAR_RE = re.compile(r"(?<![0-9])(?:19|20)\d{2}(?![0-9])")

_NOISE_NAME_SEGMENTS = {
    "transparencia", "fileadmin", "documentos", "infopublica",
    "content", "files", "docs", "public", "wp-content", "uploads",
    "media", "assets", "data", "datos",
}


@dataclass
class GroupingProposal:
    path_template: str
    dimensions: List[Dict[str, Any]] = field(default_factory=list)
    matched_urls: List[str] = field(default_factory=list)
    file_types: Dict[str, int] = field(default_factory=dict)
    suggested_name: str = ""
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _classify_segment(seg: str) -> Tuple[Optional[str], str]:
    """Devuelve (kind, value_normalized) o (None, seg) si no encaja."""
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


def _template_path_segments(segments: List[str]) -> Tuple[List[str], List[Dict[str, Any]]]:
    template: List[str] = []
    dims: List[Dict[str, Any]] = []
    for i, seg in enumerate(segments):
        kind, value = _classify_segment(seg)
        if kind:
            template.append("{" + kind + "}")
            dims.append({"name": kind, "kind": kind, "segment_index": i, "in_filename": False, "value": value})
        else:
            template.append(seg)
    return template, dims


def _template_filename(filename: str, segment_index: int) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Detecta un patrón de año dentro del nombre de fichero."""
    m = _FILENAME_YEAR_RE.search(filename)
    if not m:
        return filename, None
    try:
        v = int(m.group(0))
    except ValueError:
        return filename, None
    if not (1990 <= v <= _CURRENT_YEAR + 1):
        return filename, None
    templated = filename[: m.start()] + "{year}" + filename[m.end():]
    return templated, {
        "name": "year",
        "kind": "year",
        "segment_index": segment_index,
        "in_filename": True,
        "value": str(v),
    }


def _humanize(token: str) -> str:
    return token.replace("-", " ").replace("_", " ").strip()


def _suggested_name(constant_path_segments: List[str], templated_filename: str, dims: List[Dict[str, Any]]) -> str:
    parts: List[str] = []
    for seg in constant_path_segments:
        if seg.startswith("{") or not seg:
            continue
        if seg.lower() in _NOISE_NAME_SEGMENTS:
            continue
        parts.append(_humanize(seg))
    base = templated_filename.rsplit(".", 1)[0] if "." in templated_filename else templated_filename
    if base and not base.startswith("{"):
        parts.append(_humanize(base))
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


def _confidence(*, num_urls: int, num_constants: int, single_file_type: bool, has_typed_dim: bool) -> float:
    score = 0.0
    if num_urls >= 5:
        score += 0.4
    elif num_urls >= 3:
        score += 0.3
    elif num_urls >= 2:
        score += 0.15
    if num_constants >= 2:
        score += 0.2
    if single_file_type:
        score += 0.2
    if has_typed_dim:
        score += 0.2
    return min(score, 1.0)


def infer(leaf_urls: List[Dict[str, Any]]) -> List[GroupingProposal]:
    """
    Genera propuestas de agrupación a partir de URLs hoja.

    Args:
        leaf_urls: lista de dicts con al menos `url`. Opcionales: `file_type`,
                   `source_page`, `depth`, `anchor_text`.

    Returns:
        Lista de GroupingProposal ordenada por (confidence desc, num_urls desc, template asc).
    """
    grouped: Dict[Tuple[str, str, Tuple[str, ...]], List[Dict[str, Any]]] = defaultdict(list)
    grouped_dims: Dict[Tuple[str, str, Tuple[str, ...]], List[List[Dict[str, Any]]]] = defaultdict(list)

    for entry in leaf_urls:
        url = entry.get("url")
        if not url:
            continue
        parsed = urlparse(url)
        segments = [s for s in parsed.path.split("/") if s]
        if not segments:
            continue

        filename = segments[-1]
        path_only_segments = segments[:-1]

        template_path, path_dims = _template_path_segments(path_only_segments)
        templated_fname, fname_dim = _template_filename(filename, len(path_only_segments))

        full_template = template_path + [templated_fname]
        entry_dims = list(path_dims)
        if fname_dim:
            entry_dims.append(fname_dim)

        key = (parsed.scheme, parsed.netloc, tuple(full_template))
        grouped[key].append(entry)
        grouped_dims[key].append(entry_dims)

    proposals: List[GroupingProposal] = []
    for key, entries in grouped.items():
        scheme, netloc, template_tuple = key
        template_segs = list(template_tuple)
        path_template = f"{scheme}://{netloc}/" + "/".join(template_segs)

        dim_values: Dict[str, set] = defaultdict(set)
        for entry_dims in grouped_dims[key]:
            for d in entry_dims:
                dim_values[d["name"]].add(d["value"])

        dims_out: List[Dict[str, Any]] = []
        seen_names: set = set()
        if grouped_dims[key]:
            for d in grouped_dims[key][0]:
                if d["name"] in seen_names:
                    continue
                seen_names.add(d["name"])
                dims_out.append({
                    "name": d["name"],
                    "kind": d["kind"],
                    "segment_index": d["segment_index"],
                    "in_filename": d["in_filename"],
                    "sample_values": sorted(dim_values[d["name"]]),
                })

        urls = [e["url"] for e in entries]
        file_types_count: Dict[str, int] = defaultdict(int)
        for e in entries:
            ft = (e.get("file_type") or "unknown").lower()
            file_types_count[ft] += 1
        single_ft = len(file_types_count) == 1

        num_constants = sum(1 for s in template_segs[:-1] if s and not s.startswith("{"))
        has_typed_dim = any(d["kind"] in ("year", "month", "quarter", "date") for d in dims_out)

        if num_constants == 0 and not dims_out:
            continue

        templated_fname = template_segs[-1] if template_segs else ""
        suggested = _suggested_name(template_segs[:-1], templated_fname, dims_out)
        confidence = _confidence(
            num_urls=len(entries),
            num_constants=num_constants,
            single_file_type=single_ft,
            has_typed_dim=has_typed_dim,
        )

        proposals.append(GroupingProposal(
            path_template=path_template,
            dimensions=dims_out,
            matched_urls=urls,
            file_types=dict(file_types_count),
            suggested_name=suggested,
            confidence=confidence,
        ))

    proposals.sort(key=lambda p: (-p.confidence, -len(p.matched_urls), p.path_template))
    return proposals
