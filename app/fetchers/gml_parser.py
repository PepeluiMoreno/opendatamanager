"""
Parser GML → registros con geometría GeoJSON (stdlib, sin GDAL).

Convierte un documento GML (típico de un Download Service INSPIRE: Catastro, IGN)
en la MISMA forma de salida que cualquier otro recurso de ODM: una lista de
registros (dicts) que el dataset/JSONL sirve por la API. Así el consumidor (SIPI)
lo trata igual que a cualquier otro dataset, en vez de bajar y parsear un fichero.

Principio ODM (productor-neutro): se conservan los NOMBRES ORIGINALES de los
campos del GML y la geometría se emite como GeoJSON con las COORDENADAS NATIVAS
del fichero (sin reproyectar), añadiendo `srsName` para que el consumidor fije el
SRID y, si procede, reproyecte. El mapeo semántico
(nationalCadastralReference→referencia_catastral, etc.) es de SIPI, no de aquí.

Geometrías soportadas (las que aparecen en CP/BU/AD): Point, MultiPoint,
LineString, MultiCurve/MultiLineString, Polygon/Surface, MultiSurface/
MultiPolygon/CompositeSurface. Una geometría por feature (la primera encontrada).

AVISO sobre el ORDEN DE EJES: se respeta tal cual viene en el GML (no se
intercambia). Para los CRS proyectados UTM ETRS89 de Catastro (EPSG:258xx, eje
E,N == x,y) el orden ya coincide con GeoJSON; para CRS geográficos (lat,lon) el
consumidor debe tenerlo en cuenta a partir de `srsName`.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

_GML_ID = (
    "{http://www.opengis.net/gml/3.2}id",
    "{http://www.opengis.net/gml}id",
)

# Tipos de geometría que disparan la conversión (nombre local, en minúsculas).
_GEOM_TYPES = {
    "point", "multipoint", "linestring", "curve", "multicurve", "multilinestring",
    "polygon", "surface", "multisurface", "multipolygon", "compositesurface",
}


def _ln(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower() if "}" in tag else tag.lower()


def _find(el: ET.Element, names: set) -> Optional[ET.Element]:
    for d in el.iter():
        if _ln(d.tag) in names:
            return d
    return None


def _findall(el: ET.Element, names: set) -> List[ET.Element]:
    return [d for d in el.iter() if _ln(d.tag) in names]


def _dim(el: ET.Element) -> int:
    try:
        return int(el.get("srsDimension") or 2)
    except (TypeError, ValueError):
        return 2


def _pairs_poslist(text: str, dim: int) -> List[List[float]]:
    nums = [float(x) for x in (text or "").split()]
    dim = max(dim, 2)
    return [[nums[i], nums[i + 1]] for i in range(0, len(nums) - dim + 1, dim)]


def _pairs_coordinates(text: str) -> List[List[float]]:
    out: List[List[float]] = []
    for tup in (text or "").split():
        xy = tup.split(",")
        if len(xy) >= 2:
            out.append([float(xy[0]), float(xy[1])])
    return out


def _ring_coords(node: ET.Element) -> List[List[float]]:
    pl = _find(node, {"poslist"})
    if pl is not None and pl.text:
        return _pairs_poslist(pl.text, _dim(pl))
    co = _find(node, {"coordinates"})
    if co is not None and co.text:
        return _pairs_coordinates(co.text)
    poss = _findall(node, {"pos"})
    if poss:
        out = []
        for p in poss:
            pts = _pairs_poslist(p.text, _dim(p))
            if pts:
                out.append(pts[0])
        return out
    return []


def _point_coords(node: ET.Element) -> Optional[List[float]]:
    pos = _find(node, {"pos"})
    if pos is not None and pos.text:
        pts = _pairs_poslist(pos.text, _dim(pos))
        return pts[0] if pts else None
    co = _find(node, {"coordinates"})
    if co is not None and co.text:
        pts = _pairs_coordinates(co.text)
        return pts[0] if pts else None
    return None


def _polygon_coords(poly_el: ET.Element) -> List[List[List[float]]]:
    rings: List[List[List[float]]] = []
    ext = _find(poly_el, {"exterior"})
    if ext is not None:
        ring = _ring_coords(ext)
        if ring:
            rings.append(ring)
    for interior in _findall(poly_el, {"interior"}):
        ring = _ring_coords(interior)
        if ring:
            rings.append(ring)
    if not rings:  # Surface/PolygonPatch sin <exterior> explícito reconocible
        ring = _ring_coords(poly_el)
        if ring:
            rings.append(ring)
    return rings


def _multipolygon_coords(el: ET.Element) -> List[List[List[List[float]]]]:
    polys = []
    for m in _findall(el, {"surfacemember", "polygonmember"}):
        poly = _find(m, {"polygon", "surface"})
        if poly is None:
            poly = m
        coords = _polygon_coords(poly)
        if coords:
            polys.append(coords)
    return polys


def gml_to_geojson(geom_el: ET.Element) -> Optional[Dict[str, Any]]:
    """Convierte un elemento de geometría GML a un dict GeoJSON (coords nativas)."""
    name = _ln(geom_el.tag)
    if name == "point":
        c = _point_coords(geom_el)
        return {"type": "Point", "coordinates": c} if c else None
    if name == "multipoint":
        pts = []
        for m in _findall(geom_el, {"pointmember"}):
            p = _find(m, {"point"})
            c = _point_coords(p) if p is not None else None
            if c:
                pts.append(c)
        return {"type": "MultiPoint", "coordinates": pts} if pts else None
    if name in ("linestring", "curve"):
        c = _ring_coords(geom_el)
        return {"type": "LineString", "coordinates": c} if c else None
    if name in ("multicurve", "multilinestring"):
        lines = []
        for m in _findall(geom_el, {"curvemember", "linestringmember"}):
            ls = _find(m, {"linestring", "curve"})
            if ls is None:
                ls = m
            c = _ring_coords(ls)
            if c:
                lines.append(c)
        return {"type": "MultiLineString", "coordinates": lines} if lines else None
    if name in ("polygon", "surface"):
        c = _polygon_coords(geom_el)
        return {"type": "Polygon", "coordinates": c} if c else None
    if name in ("multisurface", "multipolygon", "compositesurface"):
        c = _multipolygon_coords(geom_el)
        return {"type": "MultiPolygon", "coordinates": c} if c else None
    return None


def _srsname(el: ET.Element) -> Optional[str]:
    if el.get("srsName"):
        return el.get("srsName")
    for d in el.iter():
        if d.get("srsName"):
            return d.get("srsName")
    return None


def _has_geometry(el: ET.Element) -> bool:
    return _find(el, _GEOM_TYPES) is not None


def _feature_elements(root: ET.Element) -> List[ET.Element]:
    """Localiza los elementos-feature, sea cual sea el envoltorio del GML."""
    members = (
        root.findall(".//{http://www.opengis.net/wfs/2.0}member")
        or root.findall(".//{http://www.opengis.net/gml/3.2}featureMember")
        or root.findall(".//{http://www.opengis.net/gml}featureMember")
    )
    if members:
        feats = [k for m in members for k in list(m)]
        if feats:
            return feats
    plural = (
        root.findall(".//{http://www.opengis.net/gml/3.2}featureMembers")
        or root.findall(".//{http://www.opengis.net/gml}featureMembers")
    )
    if plural:
        feats = [k for c in plural for k in list(c)]
        if feats:
            return feats
    # Fallback agnóstico: elementos (a uno o dos niveles) que contienen geometría.
    feats = [el for el in root if _has_geometry(el)]
    if feats:
        return feats
    return [g for el in root for g in el if _has_geometry(g)]


def _feature_to_record(f: ET.Element) -> Dict[str, Any]:
    rec: Dict[str, Any] = {}
    for attr in _GML_ID:
        if f.get(attr):
            rec["gml_id"] = f.get(attr)
            break

    geom_done = False
    for child in f:
        ln = _ln(child.tag)  # minúscula: solo para detectar tipo de geometría
        orig = child.tag.rsplit("}", 1)[-1] if "}" in child.tag else child.tag  # clave: nombre original
        geom = child if ln in _GEOM_TYPES else _find(child, _GEOM_TYPES)
        if geom is not None:
            if not geom_done:
                gj = gml_to_geojson(geom)
                if gj is not None:
                    rec["geometry"] = gj
                    srs = _srsname(geom)
                    if srs:
                        rec["srsName"] = srs
                    geom_done = True
            continue  # geometrías (primaria ya tomada, o secundarias) no van como escalar
        # Propiedad escalar: hoja con texto (se conserva el NOMBRE ORIGINAL del campo).
        if len(child) == 0 and child.text and child.text.strip():
            rec[orig] = child.text.strip()
    return rec


def parse_gml(content: bytes, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Parsea un GML a registros {campos originales + geometry (GeoJSON) + srsName}."""
    root = ET.fromstring(content)
    return [_feature_to_record(f) for f in _feature_elements(root)]
