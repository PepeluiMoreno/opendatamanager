from abc import ABC, abstractmethod
from typing import Any, Dict

RawData = Any
ParsedData = Any
DomainData = Any


class BaseFetcher(ABC):
    """
    Contrato para todos los fetchers.
    Pipeline: fetch() → parse() → normalize()
    """

    def __init__(self, params: Dict[str, str]):
        """
        Args:
            params: Diccionario con los parámetros necesarios (ej: url, headers, etc.)
        """
        self.params = params
        self.num_workers = int(params.get("num_workers", 1))

    @property
    def is_parallelizable(self) -> bool:
        """
        Indica si este fetcher puede ejecutarse con workers en paralelo.

        Returns:
            True si num_workers > 1, False en caso contrario
        """
        return self.num_workers > 1

    @abstractmethod
    def fetch(self) -> RawData:
        """Descarga o lee datos crudos desde la fuente"""
        pass

    @abstractmethod
    def parse(self, raw: RawData) -> ParsedData:
        """Normaliza estructura (JSON → dict, XML → dict, CSV → list, etc.)"""
        pass

    @abstractmethod
    def normalize(self, parsed: ParsedData) -> DomainData:
        """Transforma a formato listo para upsert en core.models"""
        pass

    def execute(self) -> DomainData:
        """Ejecuta el pipeline completo"""
        raw = self.fetch()
        parsed = self.parse(raw)
        normalized = self.normalize(parsed)
        return normalized
