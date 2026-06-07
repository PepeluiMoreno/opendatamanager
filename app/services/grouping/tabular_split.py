"""Separación tabular-vs-prosa — capacidad genérica del inferer.

Doctrina: los formatos tabulares (xlsx/xls/csv/tsv/ods) son DATO por naturaleza,
nunca censo. Cuando el inferer los agrupa dentro de una propuesta MIXTA (un
bundle que mezcla prosa PDF con hojas de cálculo), su dato queda sepultado: el
bundle va al censo y nadie lo extrae.

`carve_tabular_series` devuelve series propias para esas hojas tabulares
sepultadas, reusando `infer` sobre el subconjunto, para que el llamador pueda
promoverlas como datos. NO toca las que ya viven en una propuesta íntegramente
tabular (serie de datos ya limpia): esas no se duplican.

Función pura: sin red ni BD, y sin conocimiento de ningún portal concreto.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import urlparse

from .inferer import infer
from .models import GroupingProposal

# Formatos cuya sola presencia ya garantiza estructura tabular extraíble.
TABULAR_FORMATS = ("xlsx", "xls", "csv", "tsv", "ods")


def _formato(hoja: Dict[str, Any]) -> str:
    """Formato de una hoja: su `file_type` declarado o, en su defecto, la
    extensión del path de la URL. Siempre en minúsculas, sin punto."""
    ft = (hoja.get("file_type") or "").lower().lstrip(".")
    if ft:
        return ft
    ext = os.path.splitext(urlparse(hoja.get("url", "")).path)[1]
    return ext.lower().lstrip(".")


def carve_tabular_series(
    leaf_urls: List[Dict[str, Any]],
    proposals: Sequence[GroupingProposal],
    *,
    tabular_formats: Sequence[str] = TABULAR_FORMATS,
    path_root: Optional[str] = None,
) -> List[GroupingProposal]:
    """Series propias para las hojas tabulares hoy sepultadas en propuestas
    MIXTAS (las que contienen algún formato no-tabular, p. ej. PDF de prosa).

    Args:
        leaf_urls: las mismas hojas que se pasaron a `infer`.
        proposals: la salida de `infer(leaf_urls)`.
        tabular_formats: formatos considerados dato (default: xlsx/xls/csv/tsv/ods).
        path_root: se reenvía a `infer` para el re-agrupado, si procede.

    Returns:
        Lista (posiblemente vacía) de GroupingProposal NUEVAS. No muta la entrada.
        El llamador las añade a sus propuestas y las promueve como 'datos'.
    """
    tabular = {f.lower() for f in tabular_formats}

    # ¿La propuesta que contiene cada URL es mixta (tiene algún no-tabular)?
    mixta_de_url: Dict[str, bool] = {}
    for p in proposals:
        es_mixta = any(k.lower() not in tabular for k in (p.file_types or {}))
        for u in p.matched_urls:
            mixta_de_url[u] = es_mixta

    sepultadas = [
        h for h in leaf_urls
        if _formato(h) in tabular and mixta_de_url.get(h.get("url"), False)
    ]
    if not sepultadas:
        return []

    return list(infer(sepultadas, path_root=path_root))
