"""
Tests del AtomCrawlerFetcher (dual-modo). Sin red.
  · discover(): jerarquía INSPIRE sintética de 2 niveles -> URLs hoja.
  · stream():   descarga (mock) un ZIP+GML REAL, lo extrae y lo parsea con el
    gml_parser de producción, etiquetando cada registro con municipio.
"""
import io
import json
import zipfile
import pytest
from app.fetchers.atom_crawler_fetcher import AtomCrawlerFetcher

# ── Feeds para discover() ─────────────────────────────────────────────────────
SERVICIO = "http://cat/CP/ES.SDGC.CP.atom.xml"
GERENCIA = "http://cat/CP/11/cadiz.atom.xml"
ZIP_JEREZ = "http://cat/CP/11/A.ES.SDGC.CP.11020.zip"
ZIP_CADIZ = "http://cat/CP/11/A.ES.SDGC.CP.11012.zip"

FEED_SERVICIO = f"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
  <entry><title>Cádiz</title><id>{GERENCIA}</id>
    <link type="application/atom+xml" href="{GERENCIA}"/></entry></feed>"""
FEED_GERENCIA = f"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
  <entry><title>11020 JEREZ</title><id>{ZIP_JEREZ}</id><link rel="enclosure" href="{ZIP_JEREZ}"/></entry>
  <entry><title>11012 CADIZ</title><id>{ZIP_CADIZ}</id><link rel="enclosure" href="{ZIP_CADIZ}"/></entry></feed>"""

# ── GML real (una parcela CP con geometría MultiSurface, EPSG:25830) ──────────
GML = """<?xml version="1.0" encoding="UTF-8"?>
<gml:FeatureCollection xmlns:gml="http://www.opengis.net/gml/3.2"
    xmlns:cp="http://inspire.ec.europa.eu/schemas/cp/4.0">
  <gml:featureMember>
    <cp:CadastralParcel gml:id="ES.SDGC.CP.9252401VK3795C">
      <cp:nationalCadastralReference>9252401VK3795C</cp:nationalCadastralReference>
      <cp:areaValue uom="m2">350.0</cp:areaValue>
      <cp:geometry>
        <gml:MultiSurface srsName="urn:ogc:def:crs:EPSG::25830">
          <gml:surfaceMember>
            <gml:Polygon>
              <gml:exterior><gml:LinearRing>
                <gml:posList srsDimension="2">0 0 0 10 10 10 10 0 0 0</gml:posList>
              </gml:LinearRing></gml:exterior>
            </gml:Polygon>
          </gml:surfaceMember>
        </gml:MultiSurface>
      </cp:geometry>
    </cp:CadastralParcel>
  </gml:featureMember>
</gml:FeatureCollection>"""


def _zip_bytes(gml_name="A.ES.SDGC.CP.11020.cadastralparcel.gml"):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(gml_name, GML)
    return buf.getvalue()


class _FakeResp:
    def __init__(self, *, text="", content=b""):
        self.text = text
        self.content = content
    def raise_for_status(self):
        pass


# ── DISCOVER ──────────────────────────────────────────────────────────────────
class TestDiscover:
    def test_dos_niveles(self):
        f = AtomCrawlerFetcher({"url": SERVICIO})
        f._request = lambda *a, **k: _FakeResp(text={SERVICIO: FEED_SERVICIO, GERENCIA: FEED_GERENCIA}[a[2]])
        urls = sorted(h["url"] for h in f.discover())
        assert urls == sorted([ZIP_JEREZ, ZIP_CADIZ])

    def test_filtro(self):
        f = AtomCrawlerFetcher({"url": SERVICIO, "filtro_incluir": json.dumps(["11020"])})
        f._request = lambda *a, **k: _FakeResp(text={SERVICIO: FEED_SERVICIO, GERENCIA: FEED_GERENCIA}[a[2]])
        assert [h["url"] for h in f.discover()] == [ZIP_JEREZ]


# ── STREAM: extracción + parseo GML end-to-end ────────────────────────────────
class TestStreamGml:
    def _hijo(self):
        return AtomCrawlerFetcher({
            "_matched_urls": [ZIP_JEREZ],
            "_dimensions": [{"name": "municipio", "kind": "municipio"}],
            "_path_template": "http://cat/CP/11/A.ES.SDGC.CP.{municipio}.zip",
            "entry": "*.cadastralparcel.gml",
            "inner_format": "gml",
        })

    def test_extrae_parsea_y_etiqueta(self):
        f = self._hijo()
        f._request = lambda *a, **k: _FakeResp(content=_zip_bytes())
        filas = [r for chunk in f.stream() for r in chunk]
        assert len(filas) == 1
        r = filas[0]
        # campos nativos del GML (ODM neutro)
        assert r["nationalCadastralReference"] == "9252401VK3795C"
        assert r["areaValue"] == "350.0"
        assert r["gml_id"] == "ES.SDGC.CP.9252401VK3795C"
        # geometría GeoJSON con coords nativas + srsName
        assert r["geometry"]["type"] == "MultiPolygon"
        assert r["geometry"]["coordinates"][0][0][0] == [0.0, 0.0]
        assert r["srsName"] == "urn:ogc:def:crs:EPSG::25830"
        # dimensión inyectada + procedencia
        assert r["municipio"] == "11020"
        assert r["_source_file_url"] == ZIP_JEREZ

    def test_inner_format_se_infiere_del_entry(self):
        # sin inner_format: se infiere de la extensión .gml del fichero extraído
        f = AtomCrawlerFetcher({
            "_matched_urls": [ZIP_JEREZ],
            "_dimensions": [{"name": "municipio"}],
            "_path_template": "http://cat/CP/11/A.ES.SDGC.CP.{municipio}.zip",
            "entry": "*.cadastralparcel.gml",
        })
        f._request = lambda *a, **k: _FakeResp(content=_zip_bytes())
        filas = [r for chunk in f.stream() for r in chunk]
        assert filas[0]["nationalCadastralReference"] == "9252401VK3795C"

    def test_fichero_corrupto_se_omite_sin_tumbar(self):
        f = self._hijo()
        f.params["_matched_urls"] = [ZIP_JEREZ, "http://cat/CP/11/A.ES.SDGC.CP.99999.zip"]
        def fake(*a, **k):
            return _FakeResp(content=_zip_bytes() if a[2] == ZIP_JEREZ else b"no es un zip")
        f._request = fake
        filas = [r for chunk in f.stream() for r in chunk]
        assert len(filas) == 1   # el bueno pasa, el corrupto se omite

    def test_sin_matched_urls_falla(self):
        with pytest.raises(RuntimeError):
            list(AtomCrawlerFetcher({"url": SERVICIO}).stream())
