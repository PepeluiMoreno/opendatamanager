"""
Servicio de inferencia de agrupaciones para WebTreeFetcher.

Función única `infer(leaf_urls, path_root=None)` que produce
una lista de `GroupingProposal` a partir de URLs hoja descubiertas.

No hay plugins ni clases — un solo algoritmo basado en:
  - prefijo común máximo (auto o explícito vía path_root)
  - clasificador de segmentos (year/month/quarter/date)
  - templating + grouping por path idéntico
"""

from .inferer import infer
from .models import GroupingProposal

__all__ = ["infer", "GroupingProposal"]
