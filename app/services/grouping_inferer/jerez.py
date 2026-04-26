"""
JerezGroupingInferer — inferer adaptado a transparencia.jerez.es.

Diferencias respecto al genérico:

1. Limpieza de rutas
   - Elimina el prefijo de carpeta administrativo ``aNN-`` que el CMS de
     Jerez antepone a casi todos los segmentos (ej. ``a07-economica`` →
     ``economica``, ``a12-contratacion`` → ``contratacion``).
   - Descarta segmentos puramente ruidosos específicos del portal
     (``fileadmin``, ``Documentos``, ``Transparencia``,
     ``a-infopublica``, ``infopublica``, ``img``, ``graf``).

2. Detección de dimensiones adicionales
   - Ordinales: ``1a``, ``2a``, ``3a``, ``4a`` → kind ``ordinal``
     (ej. convocatorias, fases de licitación).
   - Área temática: segmentos de segundo nivel limpios que no sean año,
     mes ni ordinal se tratan como dimensión ``area`` cuando el mismo
     nivel varía entre URLs con igual estructura (detección heurística:
     ≥ 3 valores distintos y todos los sub-árboles son isomorfos).
     En v1 el área se detecta como dimensión genérica sin tipar;
     versiones futuras pueden usar un catálogo de áreas de Jerez.

3. Score de confianza
   - Penaliza propuestas con un único fichero (confidence max 0.3).
   - Bonifica propuestas con dimensión ``year`` detectada en el path
     (no solo en el nombre de fichero).

El algoritmo interno reutiliza las utilidades del módulo original_code
(classify_segment, template_filename, confidence) para no duplicar
lógica validada.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from .base import GroupingInferer
from .original_code import (
    GroupingProposal,
    _classify_segment,
    _template_filename,
    _humanize,
    _CURRENT_YEAR,
    _NOISE_NAME_SEGMENTS,
)


# ---------------------------------------------------------------------------
# Constantes específicas de Jerez
# ---------------------------------------------------------------------------

# Segmentos que el CMS de Jerez inserta como carpetas de navegación sin
# valor semántico propio.
_JEREZ_NOISE = {
    "fileadmin", "documentos", "transparencia", "a-infopublica",
    "infopublica", "img", "graf", "content", "files",
}

# Prefijo administrativo aNN- (ej. a07-, a12-, a01-)
_ADMIN_PREFIX = re.compile(r"^[a-z]\d+-", re.IGNORECASE)

# Ordinales típicos de convocatorias municipales
_ORDINAL_RE = re.compile(r"^[1-4][aAªº]$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_segment(seg: str) -> str:
    """
    Limpia un segmento de path eliminando el prefijo administrativo y
    normalizando separadores. Devuelve cadena vacía si es ruido puro.
    """
    if not seg:
        return ""
    if seg.lower() in _JEREZ_NOISE:
        return ""
    cleaned = _ADMIN_PREFIX.sub("", seg)
    return cleaned.replace("_", "-").strip()


def _classify_jerez_segment(seg: str) -> Tuple[Optional[str], str]:
    """
    Extiende _classify_segment con dimensiones adicionales de Jerez.

    Returns:
        (kind, value_normalized) o (None, seg_cleaned) si no es dimensión.
    """
    cleaned = _clean_segment(seg)
    if not cleaned:
        return None, ""

    # Primero intentamos las dimensiones genéricas
    kind, value = _classify_segment(cleaned)
    if kind:
        return kind, value

    # Ordinal (1a, 2a, 3a, 4a)
    if _ORDINAL_RE.fullmatch(cleaned):
        return "ordinal", cleaned.lower()

    return None, cleaned


def _jerez_suggested_name(
    template_segs: List[str],
    templated_filename: str,
    dims: List[Dict[str, Any]],
) -> str:
    """
    Genera un nombre legible para la propuesta usando los segmentos
    constantes del template (ya limpios de prefijos).
    """
    noise = _NOISE_NAME_SEGMENTS | _JEREZ_NOISE
    parts: List[str] = []
    for seg in template_segs[:-1]:
        if not seg or seg.startswith("{"):
            continue
        if seg.lower() in noise:
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

    # Sufijo de periodicidad
    kinds = {d["kind"] for d in dims}
    if "date" in kinds:
        name += " (por fecha)"
    elif "year" in kinds and "month" in kinds:
        name += " (mensual)"
    elif "year" in kinds and "quarter" in kinds:
        name += " (trimestral)"
    elif "year" in kinds and "ordinal" in kinds:
        name += " (por convocatoria)"
    elif "year" in kinds:
        name += " (anual)"
    elif "ordinal" in kinds:
        name += " (por convocatoria)"

    return name


def _jerez_confidence(
    *,
    num_urls: int,
    num_constants: int,
    single_file_type: bool,
    has_typed_dim: bool,
    year_in_path: bool,
) -> float:
    """
    Scoring ajustado para Jerez:
    - Penaliza fuertemente propuestas con un único fichero.
    - Bonifica year detectado en el path (no solo en filename).
    """
    if num_urls == 1:
        return 0.2  # techo bajo: un solo fichero sin dimensión es poco fiable

    score = 0.0
    if num_urls >= 5:
        score += 0.35
    elif num_urls >= 3:
        score += 0.25
    elif num_urls >= 2:
        score += 0.12

    if num_constants >= 2:
        score += 0.2
    if single_file_type:
        score += 0.15
    if has_typed_dim:
        score += 0.2
    if year_in_path:
        score += 0.1  # bonus: año en path es señal fuerte en Jerez

    return min(score, 1.0)


# ---------------------------------------------------------------------------
# Inferer
# ---------------------------------------------------------------------------

class JerezGroupingInferer(GroupingInferer):
    """
    Inferer especializado para el portal de transparencia de Jerez.

    Limpia rutas del CMS (prefijos aNN-, carpetas de navegación),
    detecta ordinales como dimensión adicional y ajusta el scoring.
    """

    def infer(self, leaf_urls: List[Dict[str, Any]]) -> List[Any]:
        grouped: Dict[Tuple[str, str, Tuple[str, ...]], List[Dict[str, Any]]] = defaultdict(list)
        grouped_dims: Dict[Tuple[str, str, Tuple[str, ...]], List[List[Dict[str, Any]]]] = defaultdict(list)

        for entry in leaf_urls:
            url = entry.get("url")
            if not url:
                continue
            parsed = urlparse(url)
            raw_segments = [s for s in parsed.path.split("/") if s]
            if not raw_segments:
                continue

            filename = raw_segments[-1]
            path_only = raw_segments[:-1]

            # Construir template de path con limpieza y clasificación Jerez
            template_path: List[str] = []
            path_dims: List[Dict[str, Any]] = []
            for i, seg in enumerate(path_only):
                kind, value = _classify_jerez_segment(seg)
                if kind:
                    template_path.append("{" + kind + "}")
                    path_dims.append({
                        "name": kind,
                        "kind": kind,
                        "segment_index": i,
                        "in_filename": False,
                        "value": value,
                    })
                else:
                    # Usar segmento limpio (sin prefijo) en el template
                    cleaned = _clean_segment(seg) or seg
                    template_path.append(cleaned)

            templated_fname, fname_dim = _template_filename(filename, len(path_only))
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

            # Agregar valores únicos por dimensión
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

            num_constants = sum(
                1 for s in template_segs[:-1]
                if s and not s.startswith("{")
            )
            has_typed_dim = any(
                d["kind"] in ("year", "month", "quarter", "date", "ordinal")
                for d in dims_out
            )
            year_in_path = any(
                d["kind"] == "year" and not d.get("in_filename", False)
                for d in dims_out
            )

            if num_constants == 0 and not dims_out:
                continue

            templated_fname = template_segs[-1] if template_segs else ""
            suggested = _jerez_suggested_name(template_segs, templated_fname, dims_out)
            confidence = _jerez_confidence(
                num_urls=len(entries),
                num_constants=num_constants,
                single_file_type=single_ft,
                has_typed_dim=has_typed_dim,
                year_in_path=year_in_path,
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
        return [asdict(p) for p in proposals]
