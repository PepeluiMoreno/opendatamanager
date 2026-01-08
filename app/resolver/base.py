# app/resolver/base.py
from abc import ABC, abstractmethod
from typing import Any

RawData = Any
ParsedData = Any
DomainData = Any

class BaseResolver(ABC):
    """
    Contrato mínimo que cualquier implementación debe cumplir.
    El FetcherManager solo habla con este contrato.
    """
    @abstractmethod
    def fetch(self) -> RawData:
        """Descarga o lee datos crudos"""

    @abstractmethod
    def parse(self, raw: RawData) -> ParsedData:
        """Normaliza estructura (JSON → dict, XML → dict, etc.)"""

    @abstractmethod
    def normalize(self, parsed: ParsedData) -> DomainData:
        """Devuelve lista/dict listo para upsert en core.models"""