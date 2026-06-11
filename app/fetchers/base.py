from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, List
import time
import logging
import requests

logger = logging.getLogger(__name__)

RawData = Any
ParsedData = Any
DomainData = Any


class BaseSpecies(ABC):
    """Raíz común de toda especie (Fetcher o Discoverer).

    Aporta lo transversal —inicialización de params y peticiones HTTP con
    reintentos— sin imponer un contrato de extracción ni de descubrimiento.
    De aquí cuelgan dos roles distintos:
      · BaseFetcher    → extrae una fuente y produce registros.
      · BaseDiscoverer → lee un índice y propone recursos-hijo (Fetchers).
    Una especie puede jugar ambos roles heredando de los dos (los duales:
    Catálogo DCAT, Web Tree, Compressed File).
    """

    def __init__(self, params: Dict[str, str]):
        self.params = params
        self.num_workers = int(params.get("num_workers", 1))
        self._max_retries = int(params.get("max_retries", 5))
        self._retry_backoff = float(params.get("retry_backoff", 2.0))
        # Resume protocol: las especies que soportan reanudación a media corriente
        # actualizan este dict tras cada "savepoint" (página, pivote, etc.).
        self.current_state: Dict[str, Any] = {}
        # Estadísticas de perfilado (descubrimiento/extracción), leídas por el manager.
        self.profile_stats: Dict[str, Any] = {}

    @property
    def is_parallelizable(self) -> bool:
        return self.num_workers > 1

    def _request(self, session_or_none, method: str, url: str, **kwargs) -> requests.Response:
        """Petición HTTP con reintentos ante Timeout/ConnectionError y cortesía 429/503.

        - En cada reintento el timeout se multiplica por (1 + intento).
        - La espera entre reintentos sigue backoff exponencial: backoff^intento.
        - Tras un ConnectionError se crea una nueva sesión para limpiar el estado TCP.
        """
        base_timeout = kwargs.pop("timeout", int(self.params.get("timeout", 30)))
        http = session_or_none

        for attempt in range(self._max_retries + 1):
            try:
                effective_timeout = base_timeout * (1 + attempt)
                caller = http if http else requests
                response = caller.request(method, url, timeout=effective_timeout, **kwargs)
                # 429/503 no son fallos definitivos: respetamos Retry-After si llega,
                # si no backoff. Así no maltratamos portales frágiles.
                if response.status_code in (429, 503):
                    if attempt >= self._max_retries:
                        raise RuntimeError(
                            f"Agotados {self._max_retries} reintentos en {url}: "
                            f"HTTP {response.status_code}"
                        )
                    wait = self._retry_after_seconds(response, attempt)
                    logger.warning(
                        f"[CORTESÍA {attempt + 1}/{self._max_retries}] {url} — "
                        f"HTTP {response.status_code}, esperando {wait:.0f}s"
                    )
                    time.sleep(wait)
                    continue
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
                if isinstance(exc, requests.exceptions.ConnectionError) and http is not None:
                    http = requests.Session()
                time.sleep(wait)

    def _retry_after_seconds(self, response: requests.Response, attempt: int) -> float:
        """Segundos a esperar tras 429/503: respeta Retry-After (segundos o fecha
        HTTP) y, en su defecto, aplica backoff exponencial."""
        from email.utils import parsedate_to_datetime
        from datetime import datetime, timezone

        ra = response.headers.get("Retry-After")
        if ra:
            try:
                return max(0.0, float(ra))
            except ValueError:
                try:
                    when = parsedate_to_datetime(ra)
                    if when.tzinfo is None:
                        when = when.replace(tzinfo=timezone.utc)
                    return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())
                except Exception:
                    pass
        return float(self._retry_backoff ** (attempt + 1))


class BaseFetcher(BaseSpecies):
    """Rol EXTRAER: lee una fuente y produce registros.
    Pipeline: fetch() → parse() → normalize().
    """

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


class BaseDiscoverer(BaseSpecies):
    """Rol DESCUBRIR: lee un índice/estructura y propone recursos-hijo (Fetchers).

    No extrae datos: su producto son candidatos autodescriptivos, no registros.
    Por eso NO tiene fetch()/parse()/normalize() — un descubridor no es un fetcher.
    """

    @abstractmethod
    def propose(self) -> List[Dict[str, Any]]:
        """Devuelve una lista de candidatos. Cada candidato describe un recurso-hijo:
        suggested_name, target_fetcher_code, target_params, y opcionalmente
        matched_urls/file_types/confidence."""
        pass
