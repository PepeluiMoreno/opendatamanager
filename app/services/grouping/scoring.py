"""Score de confianza heurístico para una propuesta."""

from __future__ import annotations


def confidence(*, num_urls: int, num_constants: int, single_file_type: bool, has_typed_dim: bool) -> float:
    """Heurística [0..1]: más URLs + más segmentos constantes + extensión homogénea + dimensión tipada → más confianza."""
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
