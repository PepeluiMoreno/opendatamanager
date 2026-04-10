"""
OGCFetcher — base abstracta para servicios OGC (Open Geospatial Consortium).

Responsabilidades de esta base:
  - Construir la URL de request a partir de parámetros estándar OGC
  - Ejecutar la petición HTTP con reintentos
  - Devolver la respuesta cruda (bytes)

NO hace transformación, NO parsea, NO simplifica geometrías.

Parámetros comunes a todos los servicios OGC:
    endpoint   URL base del servicio (obligatorio)
    service    Tipo de servicio: WFS | WMS  (obligatorio)
    request    Operación: GetFeature | GetMap | GetCapabilities (obligatorio)
    version    Versión del protocolo (obligatorio, ej: 2.0.0 / 1.3.0)
    timeout    Timeout HTTP en segundos (default: 120)
"""

import logging
import urllib.request
import urllib.parse
from typing import Any, Dict

from app.fetchers.base import BaseFetcher, RawData

logger = logging.getLogger(__name__)


class OGCFetcher(BaseFetcher):
    """Base para fetchers OGC. No instanciar directamente."""

    # Subclases deben definir los parámetros específicos del servicio
    _required_params: list[str] = ["endpoint", "service", "request", "version"]

    def _validate(self) -> None:
        missing = [p for p in self._required_params if not self.params.get(p)]
        if missing:
            raise ValueError(f"{self.__class__.__name__}: parámetros obligatorios ausentes: {missing}")

    def _build_params(self) -> Dict[str, str]:
        """Construye el dict de query params OGC base. Subclases amplían."""
        return {
            "service": self.params["service"],
            "request": self.params["request"],
            "version": self.params["version"],
        }

    def _do_request(self, url: str) -> bytes:
        timeout = int(self.params.get("timeout", 120))
        req = urllib.request.Request(
            url,
            headers={"Accept": "application/json, application/xml, text/xml, image/png, */*"},
        )
        logger.info(f"{self.__class__.__name__}: GET {url[:140]}…")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()

    def fetch(self) -> RawData:
        raise NotImplementedError("Usa WFSFetcher o WMSFetcher")

    def parse(self, raw: RawData) -> Any:
        raise NotImplementedError

    def normalize(self, parsed: Any) -> Any:
        return parsed
