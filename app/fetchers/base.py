from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, List
import time
import logging
import requests

logger = logging.getLogger(__name__)

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
        self._max_retries = int(params.get("max_retries", 5))
        self._retry_backoff = float(params.get("retry_backoff", 2.0))
        # Resume protocol: fetchers that support mid-stream resumption update this dict
        # after each natural "savepoint" (page, pivot, etc.).
        # FetcherManager reads it at pause time and persists it to the execution record.
        # On resume, FetcherManager passes it back via params["_resume_state"].
        self.current_state: Dict[str, Any] = {}

    @property
    def is_parallelizable(self) -> bool:
        return self.num_workers > 1

    def _request(self, session_or_none, method: str, url: str, **kwargs) -> requests.Response:
        """
        Realiza una petición HTTP con reintentos ante Timeout y ConnectionError.

        - En cada reintento el timeout se multiplica por (1 + intento).
        - La espera entre reintentos sigue backoff exponencial: backoff^intento.
        - Tras un ConnectionError se crea una nueva sesión para limpiar el estado TCP.

        Args:
            session_or_none: requests.Session activa o None (usa requests directamente).
            method:          Verbo HTTP ('GET', 'POST', …).
            url:             URL de destino.
            **kwargs:        Argumentos adicionales para requests (params, headers, json…).
                             El 'timeout' base se toma de kwargs o de self.params.
        """
        base_timeout = kwargs.pop("timeout", int(self.params.get("timeout", 30)))
        http = session_or_none

        for attempt in range(self._max_retries + 1):
            try:
                effective_timeout = base_timeout * (1 + attempt)
                caller = http if http else requests
                response = caller.request(method, url, timeout=effective_timeout, **kwargs)
                response.raise_for_status()
                return response
            except (requests.exceptions.Timeout,
                    requests.exceptions.ConnectionError) as exc:
                if attempt >= self._max_retries:
                    raise RuntimeError(
                        f"Agotados {self._max_retries} reintentos en {url}: {exc}"
                    ) from exc
                wait = self._retry_backoff ** (attempt + 1)
                logger.warning(
                    f"[RETRY {attempt + 1}/{self._max_retries}] {url} — "
                    f"esperando {wait:.0f}s tras: {exc}"
                )
                # Nueva sesión para limpiar estado TCP tras ConnectionError
                if isinstance(exc, requests.exceptions.ConnectionError) and http is not None:
                    http = requests.Session()
                time.sleep(wait)

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

    def stream(self) -> Generator[List, None, None]:
        """Yields chunks of normalized records."""
        result = self.execute()
        if isinstance(result, list):
            if result:
                yield result
        elif isinstance(result, dict):
            yield [result]

    def execute(self) -> DomainData:
        """Ejecuta el pipeline completo"""
        raw = self.fetch()
        parsed = self.parse(raw)
        normalized = self.normalize(parsed)
        return normalized
