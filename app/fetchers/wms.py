"""
WMSFetcher — fetcher OGC WMS 1.3 (Web Map Service).

Descarga imágenes de mapa de un servicio WMS y las almacena como registros
con metadatos + referencia al fichero de imagen. Útil para capturar
cartografía de referencia por tiles o por áreas de interés.

Parámetros:

  Obligatorios:
    endpoint    URL base del servicio WMS
    layers      Nombre(s) de capa separados por coma
                  ej: IGN:mtn25,IGN:curvas
    bbox        Bounding box "minx,miny,maxx,maxy" en el CRS indicado
                  ej: -6.4,36.9,-5.3,37.9

  Opcionales:
    version     Versión WMS (default: 1.3.0)
    format      Formato imagen (default: image/png)
    crs         Sistema de referencia (default: EPSG:4326)
                  WMS 1.1.x usa SRS; WMS 1.3.0 usa CRS — se gestiona automáticamente
    styles      Estilos separados por coma (default: '')
    width       Anchura en píxeles (default: 1024)
    height      Altura en píxeles (default: 1024)
    timeout     Timeout HTTP en segundos (default: 120)

El registro devuelto contiene:
  {
    "layers": "...", "bbox": "...", "crs": "...",
    "width": N, "height": N, "format": "...",
    "url": "<URL completa de la imagen>"
  }
El contenido binario de la imagen NO se almacena en el registro JSONL.
"""

import logging
import urllib.parse
from typing import Any, Dict, List

from app.fetchers.ogc import OGCFetcher
from app.fetchers.base import RawData, ParsedData, DomainData

logger = logging.getLogger(__name__)


class WMSFetcher(OGCFetcher):
    """Fetcher OGC WMS 1.3.0. Devuelve metadatos + URL de imagen, no el binario."""

    _required_params = ["endpoint", "layers", "bbox"]

    def _build_params(self) -> Dict[str, str]:
        version = self.params.get("version", "1.3.0")
        crs_key = "CRS" if version >= "1.3.0" else "SRS"
        return {
            "service":  "WMS",
            "request":  "GetMap",
            "version":  version,
            "layers":   self.params["layers"],
            "styles":   self.params.get("styles", ""),
            "format":   self.params.get("format", "image/png"),
            crs_key:    self.params.get("crs", "EPSG:4326"),
            "bbox":     self.params["bbox"],
            "width":    str(int(self.params.get("width", 1024))),
            "height":   str(int(self.params.get("height", 1024))),
        }

    def fetch(self) -> RawData:
        self._validate()
        qp  = self._build_params()
        url = f"{self.params['endpoint']}?{urllib.parse.urlencode(qp)}"
        logger.info(f"WMSFetcher: GetMap → {url[:140]}…")

        # Verificar que el servicio responde (HEAD request)
        self._do_request(url)   # lanza excepción si falla

        # El registro es el metadato de la imagen, no el binario
        record: Dict[str, Any] = {
            "layers":  qp["layers"],
            "bbox":    qp["bbox"],
            "crs":     qp.get("CRS") or qp.get("SRS", "EPSG:4326"),
            "width":   int(qp["width"]),
            "height":  int(qp["height"]),
            "format":  qp["format"],
            "url":     url,
        }
        return [record]

    def parse(self, raw: RawData) -> ParsedData:
        return raw

    def normalize(self, parsed: ParsedData) -> DomainData:
        return parsed
