"""
Tests del AtomDownloadDiscoverer con una jerarquía INSPIRE sintética de 2 niveles:
servicio -> gerencia -> ZIP municipal. Sin red: se inyecta _request.
"""
import json
import pytest
from app.fetchers.atom_download_discoverer import AtomDownloadDiscoverer

SERVICIO = "http://cat/CP/ES.SDGC.CP.atom.xml"
GERENCIA = "http://cat/CP/11/cadiz.atom.xml"
ZIP_JEREZ = "http://cat/CP/11/A.ES.SDGC.CP.11020.zip"
ZIP_CADIZ = "http://cat/CP/11/A.ES.SDGC.CP.11012.zip"

FEED_SERVICIO = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Servicio CP</title>
  <entry>
    <title>Gerencia de Cádiz</title>
    <id>{GERENCIA}</id>
    <link rel="alternate" type="application/atom+xml" href="{GERENCIA}"/>
  </entry>
</feed>"""

FEED_GERENCIA = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Cádiz</title>
  <entry>
    <title>11020 JEREZ DE LA FRONTERA</title>
    <id>{ZIP_JEREZ}</id>
    <link rel="enclosure" href="{ZIP_JEREZ}"/>
  </entry>
  <entry>
    <title>11012 CADIZ</title>
    <id>{ZIP_CADIZ}</id>
    <link rel="enclosure" href="{ZIP_CADIZ}"/>
  </entry>
</feed>"""

MAPA = {SERVICIO: FEED_SERVICIO, GERENCIA: FEED_GERENCIA}


class _FakeResp:
    def __init__(self, text):
        self.text = text
        self.status_code = 200
    def raise_for_status(self):
        pass


def _disc(params):
    d = AtomDownloadDiscoverer({"url": SERVICIO, **params})
    # _request(None, "GET", feed_url, timeout=...) -> url es el 3er posicional
    d._request = lambda *a, **k: _FakeResp(MAPA[a[2]])
    return d


class TestDescenso:
    def test_dos_niveles_propone_las_hojas(self):
        props = _disc({}).propose()
        urls = sorted(p["target_params"]["url"] for p in props)
        assert urls == sorted([ZIP_JEREZ, ZIP_CADIZ])
        assert all(p["target_fetcher_code"] == "Compressed File" for p in props)
        assert all(p["target_params"]["format"] == "zip" for p in props)

    def test_profile_stats(self):
        d = _disc({})
        d.propose()
        s = d.profile_stats
        assert s["feeds_leidos"] == 2          # servicio + gerencia
        assert s["hojas_encontradas"] == 2
        assert s["total_files"] == 2


class TestFiltro:
    def test_filtro_por_codigo_municipio(self):
        props = _disc({"filtro_incluir": json.dumps(["11020"])}).propose()
        assert len(props) == 1
        assert props[0]["target_params"]["url"] == ZIP_JEREZ

    def test_filtro_acepta_csv(self):
        props = _disc({"filtro_incluir": "11012"}).propose()
        assert len(props) == 1
        assert props[0]["target_params"]["url"] == ZIP_CADIZ


class TestCortesiaYChildParams:
    def test_propaga_throttle_a_hijos(self):
        props = _disc({"max_per_hour": "3500", "rate_limit_per_second": "1"}).propose()
        for p in props:
            assert p["target_params"]["max_per_hour"] == "3500"
            assert p["target_params"]["rate_limit_per_second"] == "1"

    def test_child_params_se_fusionan(self):
        props = _disc({"child_params": json.dumps({"inner_format": "gml", "entry": "*.gml"})}).propose()
        for p in props:
            assert p["target_params"]["inner_format"] == "gml"
            assert p["target_params"]["entry"] == "*.gml"


class TestMaxDepth:
    def test_max_depth_1_desciende_un_nivel_y_fuerza_hojas(self):
        # max_depth=1: servicio(0) desciende a gerencia(1); en profundidad>=1 todo
        # enlace se trata como hoja. Resultado: los 2 ZIP municipales. Confirma el
        # descenso acotado + la rama "forzar hoja".
        props = _disc({"max_depth": "1"}).propose()
        urls = sorted(p["target_params"]["url"] for p in props)
        assert urls == sorted([ZIP_JEREZ, ZIP_CADIZ])
