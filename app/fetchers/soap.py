"""
SoapFetcher — fetcher genérico para servicios web SOAP/WSDL.

Usa zeep para cargar el WSDL y llamar a una operación específica.
Soporta operaciones que devuelven un conjunto de datos (no enriquecimiento
registro a registro).

Params configurables via ResourceParam:
    wsdl_url       URL del fichero WSDL (obligatorio)
    operation      Nombre de la operación SOAP a invocar (obligatorio)
    params_json    JSON string con los parámetros de la operación,
                     ej: {"Provincia":"MADRID","Municipio":"MADRID"}
    result_path    Ruta dot-notation para extraer los datos del resultado,
                     ej: "bico.bi" o "municipieronm.mun"
                     Si no se define, devuelve el objeto completo serializado.
    timeout        Timeout en segundos (default: 60)

Ejemplo — Catastro OVC (municipios de una provincia):
    wsdl_url    = https://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/OVCCallejero.asmx?WSDL
    operation   = ObtenerMunicipios
    params_json = {"Provincia":"MADRID","Municipio":""}
    result_path = municipieronm.mun

Ejemplo — Catastro OVC (inmueble por referencia catastral):
    wsdl_url    = https://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/OVCCallejero.asmx?WSDL
    operation   = Consulta_DNPRC
    params_json = {"Provincia":"MADRID","Municipio":"MADRID","RC":"9252401VK3795C"}
    result_path = bico.bi
"""

import json
import logging
from typing import Any

from zeep import Client, Settings
from zeep.helpers import serialize_object

from app.fetchers.base import BaseFetcher, DomainData, ParsedData, RawData

logger = logging.getLogger(__name__)


def _get_nested(obj: Any, path: str) -> Any:
    """Navega un objeto zeep por ruta dot-notation, ej: 'bico.bi'."""
    for key in path.split("."):
        if obj is None:
            return None
        if isinstance(obj, dict):
            obj = obj.get(key)
        else:
            obj = getattr(obj, key, None)
    return obj


class SoapFetcher(BaseFetcher):
    """Fetcher genérico para operaciones SOAP/WSDL via zeep."""

    def fetch(self) -> RawData:
        wsdl_url  = self.params.get("wsdl_url")
        operation = self.params.get("operation")
        if not wsdl_url or not operation:
            raise ValueError("SoapFetcher requiere 'wsdl_url' y 'operation'")

        params_raw = self.params.get("params_json", "{}")
        call_params: dict = json.loads(params_raw) if isinstance(params_raw, str) else params_raw

        timeout = int(self.params.get("timeout", 60))

        logger.info(f"SoapFetcher: {wsdl_url} → {operation}({call_params})")

        settings = Settings(strict=False, xml_huge_tree=True)
        client = Client(wsdl_url, settings=settings)

        # Invocar la operación dinámicamente
        op_fn = getattr(client.service, operation, None)
        if op_fn is None:
            available = [str(s) for s in client.wsdl.services.values()]
            raise ValueError(
                f"Operación '{operation}' no encontrada en el WSDL. "
                f"Servicios disponibles: {available}"
            )

        result = op_fn(**call_params, _soapheaders=None)
        logger.info(f"SoapFetcher: respuesta recibida")
        return result

    def parse(self, raw: RawData) -> ParsedData:
        """
        Serializa el objeto zeep a dict/list Python y aplica result_path si se define.
        """
        serialized = serialize_object(raw, target_cls=dict)

        result_path = self.params.get("result_path", "").strip()
        if result_path:
            extracted = _get_nested(serialized, result_path)
            if extracted is None:
                logger.warning(f"result_path='{result_path}' no encontrado en la respuesta")
                return []
            # Si es lista, devolver tal cual; si es dict, envolver en lista
            if isinstance(extracted, list):
                return extracted
            return [extracted]

        # Sin result_path: devolver la respuesta completa como lista de un elemento
        return [serialized]

    def normalize(self, parsed: ParsedData) -> DomainData:
        return parsed
