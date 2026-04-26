"""
Paquete grouping_inferer.

Expone el registro de inferers y la fábrica get_inferer().
Retrocompatible: `from app.services.grouping_inferer import infer` sigue
funcionando vía re-export desde original_code.
"""

from .base import GroupingInferer
from .generic import GenericGroupingInferer
from .jerez import JerezGroupingInferer
from .original_code import infer, GroupingProposal  # retrocompatibilidad

INFERER_REGISTRY: dict = {
    "generic": GenericGroupingInferer,
    "jerez": JerezGroupingInferer,
}


def get_inferer(name: str, **kwargs) -> GroupingInferer:
    """
    Fábrica de inferers.

    Args:
        name: clave del registro (ej. 'generic', 'jerez').
        **kwargs: argumentos opcionales pasados al constructor.

    Raises:
        ValueError: si el nombre no está registrado.
    """
    cls = INFERER_REGISTRY.get(name)
    if cls is None:
        registered = ", ".join(sorted(INFERER_REGISTRY))
        raise ValueError(
            f"Inferer desconocido: '{name}'. Registrados: {registered}"
        )
    return cls(**kwargs)


__all__ = [
    "GroupingInferer",
    "GenericGroupingInferer",
    "JerezGroupingInferer",
    "GroupingProposal",
    "INFERER_REGISTRY",
    "get_inferer",
    "infer",
]
