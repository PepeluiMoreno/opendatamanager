"""
Tests del parser GML → registros con geometría GeoJSON (sin red, sin GDAL).

GML sintético al estilo INSPIRE:
  - CadastralParcel (CP) con MultiSurface (polígono con hueco) → MultiPolygon.
  - Address (AD) con Point.
Valida: nombres de campo originales conservados, geometría GeoJSON con coords
nativas, srsName capturado, y el dispatch por parse_structured_file('gml').
"""
from app.fetchers.gml_parser import parse_gml
from app.fetchers.file_parsers import parse_structured_file, infer_file_format


GML_CP = """<?xml version="1.0" encoding="UTF-8"?>
<gml:FeatureCollection xmlns:gml="http://www.opengis.net/gml/3.2"
                       xmlns:cp="urn:x-inspire:specification:gmlas:CadastralParcels:3.0">
  <gml:featureMember>
    <cp:CadastralParcel gml:id="ES.SDGC.CP.11020A">
      <cp:nationalCadastralReference>11020A001000010000XY</cp:nationalCadastralReference>
      <cp:areaValue uom="m2">1234.0</cp:areaValue>
      <cp:geometry>
        <gml:MultiSurface srsName="urn:ogc:def:crs:EPSG::25830">
          <gml:surfaceMember>
            <gml:Polygon>
              <gml:exterior>
                <gml:LinearRing>
                  <gml:posList srsDimension="2">0 0 10 0 10 10 0 10 0 0</gml:posList>
                </gml:LinearRing>
              </gml:exterior>
              <gml:interior>
                <gml:LinearRing>
                  <gml:posList>2 2 4 2 4 4 2 4 2 2</gml:posList>
                </gml:LinearRing>
              </gml:interior>
            </gml:Polygon>
          </gml:surfaceMember>
        </gml:MultiSurface>
      </cp:geometry>
    </cp:CadastralParcel>
  </gml:featureMember>
</gml:FeatureCollection>"""


GML_AD = """<?xml version="1.0" encoding="UTF-8"?>
<gml:FeatureCollection xmlns:gml="http://www.opengis.net/gml/3.2"
                       xmlns:ad="urn:x-inspire:specification:gmlas:Addresses:3.0">
  <gml:featureMember>
    <ad:Address gml:id="AD1">
      <ad:designator>5</ad:designator>
      <ad:position>
        <gml:Point srsName="urn:ogc:def:crs:EPSG::25830"><gml:pos>100 200</gml:pos></gml:Point>
      </ad:position>
    </ad:Address>
  </gml:featureMember>
</gml:FeatureCollection>"""


class TestCadastralParcel:
    def test_un_registro_con_campos_originales(self):
        recs = parse_gml(GML_CP.encode("utf-8"))
        assert len(recs) == 1
        r = recs[0]
        assert r["gml_id"] == "ES.SDGC.CP.11020A"
        # nombre de campo ORIGINAL (camelCase), no minusculizado
        assert r["nationalCadastralReference"] == "11020A001000010000XY"
        assert r["areaValue"] == "1234.0"

    def test_geometria_multipolygon_con_hueco(self):
        r = parse_gml(GML_CP.encode("utf-8"))[0]
        g = r["geometry"]
        assert g["type"] == "MultiPolygon"
        # un polígono, dos anillos (exterior + interior)
        assert len(g["coordinates"]) == 1
        ext, hole = g["coordinates"][0]
        assert ext == [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
        assert hole == [[2, 2], [4, 2], [4, 4], [2, 4], [2, 2]]

    def test_srsname_capturado_sin_reproyectar(self):
        r = parse_gml(GML_CP.encode("utf-8"))[0]
        assert r["srsName"] == "urn:ogc:def:crs:EPSG::25830"


class TestAddressPoint:
    def test_punto(self):
        r = parse_gml(GML_AD.encode("utf-8"))[0]
        assert r["gml_id"] == "AD1"
        assert r["designator"] == "5"
        assert r["geometry"] == {"type": "Point", "coordinates": [100, 200]}


class TestDispatch:
    def test_infer_gml(self):
        assert infer_file_format("A.ES.SDGC.CP.11020.cadastralparcel.gml") == "gml"

    def test_parse_structured_file_gml(self):
        recs = parse_structured_file(GML_CP.encode("utf-8"), "gml")
        assert len(recs) == 1
        assert recs[0]["geometry"]["type"] == "MultiPolygon"
