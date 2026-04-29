"""GroupingProposal — output del algoritmo de inferencia."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List


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
