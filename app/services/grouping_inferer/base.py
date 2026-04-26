"""
Interfaz abstracta para todos los inferers de agrupación.

Un GroupingInferer recibe la lista de URLs hoja producida por
`WebTreeFetcher.discover()` y emite propuestas de agrupación
(`GroupingProposal`) que el FetcherManager persiste como
`ResourceCandidate`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class GroupingInferer(ABC):
    """
    Contrato que deben implementar todos los inferers concretos.

    El método `infer` es puro: sin BD, sin red, sin estado mutable
    entre llamadas. El resultado es determinista para un input dado.
    """

    @abstractmethod
    def infer(self, leaf_urls: List[Dict[str, Any]]) -> List[Any]:
        """
        Infiere propuestas de agrupación a partir de URLs hoja.

        Args:
            leaf_urls: lista de dicts con al menos la clave ``url``.
                       Opcionales: ``file_type``, ``source_page``,
                       ``depth``, ``anchor_text``.

        Returns:
            Lista de GroupingProposal (dataclass o dict) ordenada por
            (confidence desc, num_urls desc, path_template asc).
        """
        ...
