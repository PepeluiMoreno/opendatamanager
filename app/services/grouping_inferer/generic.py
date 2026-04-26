"""
GenericGroupingInferer — envuelve el algoritmo original de inferencia.

Usa la implementación genérica (original_code.infer) sin modificación.
Es el inferer por defecto cuando no se especifica ninguno en la
configuración del recurso.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .base import GroupingInferer
from .original_code import infer as _original_infer


class GenericGroupingInferer(GroupingInferer):
    """
    Inferer genérico: aplica el algoritmo estándar de detección de
    dimensiones (year, month, quarter, date) sin adaptaciones
    específicas de portal.

    Es el fallback para cualquier portal no configurado explícitamente.
    """

    def infer(self, leaf_urls: List[Dict[str, Any]]) -> List[Any]:
        return _original_infer(leaf_urls)
