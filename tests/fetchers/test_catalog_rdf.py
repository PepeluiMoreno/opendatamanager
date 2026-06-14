"""Variante dcat-rdf del CatalogFetcher: parsea un feed DCAT-AP RDF y aplica el
mismo filtro/contrato que datosgob y ckan. Sin red: _request mockeado."""
from app.fetchers.catalog import CatalogFetcher

RDF_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:dcat="http://www.w3.org/ns/dcat#"
         xmlns:dct="http://purl.org/dc/terms/"
         xmlns:foaf="http://xmlns.com/foaf/0.1/">
  <dcat:Dataset rdf:about="http://x/ds1">
    <dct:title xml:lang="es">Registro de asociaciones de Prueba</dct:title>
    <dct:publisher><foaf:Agent><foaf:name>Ayuntamiento de Prueba</foaf:name></foaf:Agent></dct:publisher>
    <dcat:distribution>
      <dcat:Distribution>
        <dcat:downloadURL rdf:resource="https://x/asociaciones.csv"/>
        <dct:format>CSV</dct:format>
      </dcat:Distribution>
    </dcat:distribution>
    <dcat:distribution>
      <dcat:Distribution>
        <dcat:downloadURL rdf:resource="https://x/asociaciones.json"/>
        <dct:format>JSON</dct:format>
      </dcat:Distribution>
    </dcat:distribution>
  </dcat:Dataset>
  <dcat:Dataset rdf:about="http://x/ds2">
    <dct:title xml:lang="es">Presupuesto municipal por capitulos</dct:title>
    <dcat:distribution>
      <dcat:Distribution>
        <dcat:downloadURL rdf:resource="https://x/presupuesto.csv"/>
        <dct:format>CSV</dct:format>
      </dcat:Distribution>
    </dcat:distribution>
  </dcat:Dataset>
</rdf:RDF>"""

class _Resp:
    content = RDF_XML
    def raise_for_status(self): pass

def _f():
    f = CatalogFetcher({"catalog_type": "dcat-rdf", "catalog_api": "https://portal/feed.rdf",
                        "formats": "csv", "child_fetcher": "File Download", "max_pages": "1"})
    f._request = lambda *a, **k: _Resp()
    return f

def test_rdf_extrae_asociaciones_y_filtra():
    props = _f().propose()
    # solo el dataset de asociaciones, solo la distribución csv (formats=csv)
    assert len(props) == 1
    p = props[0]
    assert p["target_fetcher_code"] == "File Download"
    assert p["target_params"] == {"url": "https://x/asociaciones.csv", "format": "csv"}
    assert "Ayuntamiento de Prueba" in p["suggested_name"]

def test_rdf_excluye_no_asociaciones():
    # con formats=csv,json sigue habiendo 1 candidato tras prefer? sin prefer: 2 dists del mismo dataset
    f = CatalogFetcher({"catalog_type": "dcat-rdf", "catalog_api": "https://portal/feed.rdf",
                        "formats": "csv,json", "child_fetcher": "File Download", "max_pages": "1"})
    f._request = lambda *a, **k: _Resp()
    urls = sorted(p["target_params"]["url"] for p in f.propose())
    assert urls == ["https://x/asociaciones.csv", "https://x/asociaciones.json"]
