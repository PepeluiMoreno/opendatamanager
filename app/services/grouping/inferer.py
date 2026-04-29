"""
Algoritmo único de inferencia de agrupaciones.

Pipeline:
  1. Calcular el prefijo común máximo de path entre todas las URLs hoja
     (o usar `path_root` si se pasa explícito). Es el "ruido administrativo"
     constante del portal — no se necesita lista hardcoded.
  2. Strip prefijo, tokenizar el resto en segmentos.
  3. Clasificar cada segmento (year/month/quarter/date) y emitir placeholders.
  4. Agrupar URLs por path_template idéntico.
  5. Por grupo: matched_urls, dimensiones (con sample_values), file_types,
     suggested_name, confidence.

Función pura: sin BD, sin red, sin estado.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from .models import GroupingProposal
from .naming import suggested_name
from .scoring import confidence
from .templating import template_filename, template_path_segments


def _parse_path_segments(url: str) -> List[str]:
    parsed = urlparse(url)
    return [s for s in parsed.path.split("/") if s]


def _common_path_prefix_segments(all_segments: List[List[str]]) -> List[str]:
    """Prefijo común máximo a NIVEL DE SEGMENTO (no de carácter).

    Excluye el último segmento (filename) de cada URL para el cálculo.

    Cap de seguridad: el prefijo nunca consume TODOS los segmentos de path,
    se reserva al menos uno para que cada propuesta conserve un segmento
    identificador (de lo contrario, URLs hermanas perderían toda estructura).
    Para una sola URL, devuelve [] (no hay prefijo "común" significativo).
    """
    if not all_segments or len(all_segments) < 2:
        return []
    paths_only = [segs[:-1] for segs in all_segments if len(segs) >= 1]
    if not paths_only or not paths_only[0]:
        return []
    min_len = min(len(p) for p in paths_only)
    cap = max(0, min_len - 1)  # reservar al menos 1 segmento
    prefix: List[str] = []
    for i in range(cap):
        candidate = paths_only[0][i]
        if all(p[i] == candidate for p in paths_only):
            prefix.append(candidate)
        else:
            break
    return prefix


def _path_root_to_segments(path_root: str) -> List[str]:
    return [s for s in path_root.split("/") if s]


def infer(
    leaf_urls: List[Dict[str, Any]],
    *,
    path_root: Optional[str] = None,
) -> List[GroupingProposal]:
    """
    Genera propuestas de agrupación a partir de URLs hoja.

    Args:
        leaf_urls: lista de dicts con al menos `url`. Opcionales: `file_type`,
                   `source_page`, `depth`, `anchor_text`.
        path_root: si se pasa, sobreescribe el prefijo común calculado.
                   Útil cuando un crawler mezcla sub-portales con prefijos
                   distintos y el operador quiere fijar uno explícito.

    Returns:
        Lista de GroupingProposal ordenada por (confidence desc, num_urls desc, template asc).
    """
    if not leaf_urls:
        return []

    # 1. Parsear todas las URLs en (scheme, netloc, segments, original_entry)
    parsed_entries: List[Tuple[str, str, List[str], Dict[str, Any]]] = []
    for entry in leaf_urls:
        url = entry.get("url")
        if not url:
            continue
        parsed = urlparse(url)
        segments = _parse_path_segments(url)
        if not segments:
            continue
        parsed_entries.append((parsed.scheme, parsed.netloc, segments, entry))

    if not parsed_entries:
        return []

    # 2. Calcular prefijo común (override si path_root explícito)
    explicit_root = path_root is not None
    if explicit_root:
        prefix_segs = _path_root_to_segments(path_root)
    else:
        prefix_segs = _common_path_prefix_segments([segs for _, _, segs, _ in parsed_entries])

    prefix_len = len(prefix_segs)

    # 3. Agrupar por (scheme, netloc, template_post_prefix)
    grouped: Dict[Tuple[str, str, Tuple[str, ...]], List[Dict[str, Any]]] = defaultdict(list)
    grouped_dims: Dict[Tuple[str, str, Tuple[str, ...]], List[List[Dict[str, Any]]]] = defaultdict(list)

    for scheme, netloc, segments, entry in parsed_entries:
        if segments[:prefix_len] == prefix_segs:
            stripped = segments[prefix_len:]
        else:
            # Con path_root explícito, las URLs fuera del prefijo se descartan.
            # Con auto-LCM no debería pasar (el prefijo es por construcción común).
            if explicit_root:
                continue
            stripped = segments
        if not stripped:
            continue

        filename = stripped[-1]
        path_only_segments = stripped[:-1]

        template_path, path_dims = template_path_segments(path_only_segments)
        templated_fname, fname_dims = template_filename(filename, len(path_only_segments))

        full_template = template_path + [templated_fname]
        entry_dims = list(path_dims) + list(fname_dims)

        key = (scheme, netloc, tuple(full_template))
        grouped[key].append(entry)
        grouped_dims[key].append(entry_dims)

    # 4. Construir propuestas
    proposals: List[GroupingProposal] = []
    prefix_str = "/".join(prefix_segs)
    for key, entries in grouped.items():
        scheme, netloc, template_tuple = key
        template_segs = list(template_tuple)
        # path_template incluye el prefijo común para que sea reconstruible
        if prefix_str:
            path_template = f"{scheme}://{netloc}/{prefix_str}/" + "/".join(template_segs)
        else:
            path_template = f"{scheme}://{netloc}/" + "/".join(template_segs)

        # Recolectar valores de cada dimensión across URLs del grupo
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

        # Descartar grupos sin estructura: ni constantes ni dimensiones tipadas
        if num_constants == 0 and not dims_out:
            continue

        templated_fname = template_segs[-1] if template_segs else ""
        suggested = suggested_name(template_segs[:-1], templated_fname, dims_out)
        score = confidence(
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
            confidence=score,
        ))

    proposals.sort(key=lambda p: (-p.confidence, -len(p.matched_urls), p.path_template))
    return proposals
