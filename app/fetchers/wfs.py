"""
WFSFetcher — fetcher OGC WFS 2.0 (Web Feature Service).

Descarga features vectoriales de cualquier endpoint WFS compatible,
paginando automáticamente con startIndex + count hasta agotar el dataset.

Parámetros (todos via ResourceParam):

  Obligatorios:
    endpoint      URL base del servicio WFS
                    ej: https://www.catastro.meh.es/INSPIRE/CadastralParcels/ES.SDGC.CP.wfs
    typenames     Nombre(s) del tipo de feature (typeName en WFS 1.x)
                    ej: CP:CadastralParcel

  Opcionales:
    version       Versión WFS (default: 2.0.0)
    outputFormat  Formato de respuesta (default: application/json)
                    Alternativa GML: application/gml+xml; subtype=gml/3.2
    srsName       Sistema de referencia (default: EPSG:4326)
    bbox          Bounding box como "minx,miny,maxx,maxy"
                    ej: -6.4,36.9,-5.3,37.9
    cql_filter    Filtro CQL (GeoServer/MapServer)
                    ej: municipalityCode = '41091'
    count         Features por página / max por request (default: 1000)
    timeout       Timeout HTTP en segundos (default: 120)
    id_field      Campo a usar como _id en el registro normalizado (opcional)

Ejemplo — Parcelas catastrales INSPIRE (bbox Sevilla):
    endpoint      = https://www.catastro.meh.es/INSPIRE/CadastralParcels/ES.SDGC.CP.wfs
    typenames     = CP:CadastralParcel
    bbox          = -6.4,36.9,-5.3,37.9
    outputFormat  = application/gml+xml; subtype=gml/3.2
    id_field      = nationalCadastralReference

Ejemplo — Unidades administrativas IGN:
    endpoint      = https://www.ign.es/wfs/inspire-unidades-administrativas
    typenames     = au:AdministrativeUnit
    version       = 2.0.0
    cql_filter    = nationalLevel = '4'
"""

import io
import json
import logging
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

from app.fetchers.ogc import OGCFetcher
from app.fetchers.base import RawData, ParsedData, DomainData

logger = logging.getLogger(__name__)


# ── Parsers ────────────────────────────────────────────────────────────────────

def _parse_geojson(data: bytes) -> List[Dict[str, Any]]:
    obj = json.loads(data)
    records = []
    for f in obj.get("features", []):
        rec: Dict[str, Any] = {}
        if f.get("id"):
            rec["gml_id"] = f["id"]
        rec.update(f.get("properties") or {})
        records.append(rec)
    return records


def _parse_gml(data: bytes) -> List[Dict[str, Any]]:
    root = ET.fromstring(data)
    # WFS 2.0: wfs:member  |  WFS 1.x: gml:featureMember
    members = (
        root.findall(".//{http://www.opengis.net/wfs/2.0}member") or
        root.findall(".//{http://www.opengis.net/gml/3.2}featureMember") or
        root.findall(".//{http://www.opengis.net/gml}featureMember")
    )
    records = []
    for member in members:
        rec: Dict[str, Any] = {}
        for feature in member:
            gml_id = (
                feature.get("{http://www.opengis.net/gml/3.2}id") or
                feature.get("{http://www.opengis.net/gml}id")
            )
            if gml_id:
                rec["gml_id"] = gml_id
            for child in feature:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                # Solo propiedades escalares — geometrías (elementos con hijos) se omiten
                if not len(child) and child.text and child.text.strip():
                    rec[tag] = child.text.strip()
        if rec:
            records.append(rec)
    return records


# ── Fetcher ────────────────────────────────────────────────────────────────────

class WFSFetcher(OGCFetcher):
    """Fetcher OGC WFS 2.0 con paginación automática."""

    _required_params = ["endpoint", "typenames"]

    def _build_params(self) -> Dict[str, str]:
        version = self.params.get("version", "2.0.0")
        p: Dict[str, str] = {
            "service":      "WFS",
            "request":      "GetFeature",
            "version":      version,
            "typenames":    self.params["typenames"],   # WFS 2.0
            "outputFormat": self.params.get("outputFormat", "application/json"),
            "srsName":      self.params.get("srsName", "EPSG:4326"),
        }
        # WFS 1.x usa typeName (singular)
        if version.startswith("1."):
            p["typeName"] = p.pop("typenames")

        bbox = self.params.get("bbox", "").strip()
        if bbox:
            p["bbox"] = bbox

        cql = self.params.get("cql_filter", "").strip()
        if cql:
            p["CQL_FILTER"] = cql

        return p

    def fetch(self) -> RawData:
        self._validate()

        count       = int(self.params.get("count", 1000))
        resume      = self.params.get("_resume_state") or {}
        start_index = int(resume.get("start_index", 0))

        all_records: List[Dict[str, Any]] = []

        while True:
            qp = self._build_params()
            qp["count"]      = str(count)
            qp["startIndex"] = str(start_index)

            url = f"{self.params['endpoint']}?{urllib.parse.urlencode(qp)}"
            raw = self._do_request(url)

            output_fmt = qp.get("outputFormat", "application/json")
            if "json" in output_fmt:
                page = _parse_geojson(raw)
            else:
                page = _parse_gml(raw)

            logger.info(f"WFSFetcher: {len(page)} features (offset={start_index})")

            if not page:
                break

            all_records.extend(page)
            start_index += len(page)
            self.current_state = {"start_index": start_index}

            if len(page) < count:
                break   # última página

        logger.info(f"WFSFetcher: total {len(all_records)} features")
        return all_records

    def parse(self, raw: RawData) -> ParsedData:
        return raw  # ya viene como lista de dicts desde fetch()

    def normalize(self, parsed: ParsedData) -> DomainData:
        id_field = self.params.get("id_field", "").strip()
        if id_field:
            for rec in parsed:
                if id_field in rec:
                    rec["_id"] = rec[id_field]
        return parsed
