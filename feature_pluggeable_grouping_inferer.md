# Diseño de GroupingInferer plugeable (plugin)

## Visión general

Actualmente el sistema asume un único algoritmo de agrupación (GroupingInferer.infer()) para transformar la lista de URLs hoja descubiertas por WebTreeFetcher en propuestas de agrupación (GroupingProposal). Esta rigidez impide ajustar la lógica a las peculiaridades de cada portal.

La solución propuesta consiste en convertir el inferer en un mecanismo plugeable, de modo que el orquestador pueda elegir dinámicamente qué estrategia de agrupación aplicar.

De esta forma:
- WebTreeFetcher se mantiene sin cambios
- Cada portal puede tener su propio inferer especializado
- El código se organiza limpio, siguiendo el principio de responsabilidad única

---

## Piezas de código a crear/modificar

### 1. Interfaz abstracta GroupingInferer

Ubicación: app/services/grouping_inferer/base.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any

class GroupingInferer(ABC):
    @abstractmethod
    def infer(self, leaf_urls: List[Dict[str, Any]]) -> List[Any]:
        """Recibe URLs hoja y retorna lista de GroupingProposal"""
        pass

### 2. Inferer genérico

Ubicación: app/services/grouping_inferer/generic.py

from app.services.grouping_inferer.base import GroupingInferer
from app.services.grouping_inferer.original_code import infer as _original_infer

class GenericGroupingInferer(GroupingInferer):
    def infer(self, leaf_urls: List[Dict[str, Any]]) -> List[Any]:
        return _original_infer(leaf_urls)

### 3. Inferer especializado para Jerez

Ubicación: app/services/grouping_inferer/jerez.py

from .base import GroupingInferer
from typing import List, Dict, Any
from dataclasses import asdict
import re

class JerezGroupingInferer(GroupingInferer):
    NOISE_SEGMENTS = {
        "fileadmin", "Documentos", "Transparencia", "a-infopublica",
        "img", "graf", "content", "files", "wp-content", "uploads"
    }
    PREFIX_CLEAN = re.compile(r"^[a-z]\d+-")
    
    def _normalize_segment(self, seg: str) -> str:
        if not seg:
            return seg
        if seg.lower() in self.NOISE_SEGMENTS:
            return ""
        seg = self.PREFIX_CLEAN.sub("", seg)
        return seg.replace("_", "-")
    
    def infer(self, leaf_urls: List[Dict[str, Any]]) -> List[Any]:
        proposals = []
        # Lógica de agrupación adaptada a Jerez
        return [asdict(p) for p in proposals]

### 4. Registro de inferers

Ubicación: app/services/grouping_inferer/__init__.py

from .generic import GenericGroupingInferer
from .jerez import JerezGroupingInferer

INFERER_REGISTRY = {
    "generic": GenericGroupingInferer,
    "jerez": JerezGroupingInferer,
}

def get_inferer(name: str, **kwargs) -> GroupingInferer:
    cls = INFERER_REGISTRY.get(name)
    if not cls:
        raise ValueError(f"Inferer desconocido: {name}")
    return cls(**kwargs)

### 5. Modificación del orquestador

Ubicación: donde se instancia WebTreeFetcher

from app.services.grouping_inferer import get_inferer

def process_discovery(params):
    fetcher = WebTreeFetcher(params)
    leaves = fetcher.discover()

    inferer_name = params.get("grouping_inferer", "generic")
    inferer = get_inferer(inferer_name)

    proposals = inferer.infer(leaves)

    for prop in proposals:
        # persistir propuesta
        pass

### 6. Configuración del recurso

{
  "resource_id": "jerez_transparencia",
  "fetcher": "web_tree",
  "params": {
    "root_url": "https://transparencia.jerez.es",
    "max_depth": 5,
    "grouping_inferer": "jerez"
  }
}

---

## Resumen de responsabilidades

| Componente | Responsabilidad |
|------------|----------------|
| WebTreeFetcher | Descubre URLs hoja (sin cambios) |
| GroupingInferer (interfaz) | Contrato para todos los inferers |
| GenericGroupingInferer | Algoritmo genérico (actual) |
| JerezGroupingInferer | Algoritmo adaptado a Jerez |
| get_inferer() | Fábrica de inferers |
| FetcherManager | Orquesta el proceso |

---

## Ventajas

1. Sin cambios en WebTreeFetcher
2. Fácil extensión (nuevo inferer = nueva clase)
3. Configurable por recurso
4. Mantenible y testeable
5. Evolutivo (permitir inferers complejos)

---

## Próximos pasos

1. Refactorizar infer() actual dentro de GenericGroupingInferer
2. Implementar JerezGroupingInferer con mejoras
3. Modificar orquestador para usar registro
4. Añadir pruebas unitarias
5. Documentar creación de nuevos inferers