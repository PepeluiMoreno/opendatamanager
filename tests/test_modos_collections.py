"""Keystone Collections: la capacidad 'descubrir' vive en la especie, no en el
tipo Web Tree; un recurso es Colección si su especie descubre y no tiene padre."""
from types import SimpleNamespace
from app.models import Fetcher, Resource


def test_descubre_segun_modos():
    assert Fetcher(code="Web Tree", modos=["extraer", "descubrir"]).descubre is True
    assert Fetcher(code="File Download", modos=["extraer"]).descubre is False
    assert Fetcher(code="X", modos=None).descubre is False


def test_es_coleccion():
    wt = Fetcher(code="Web Tree", modos=["extraer", "descubrir"])
    fd = Fetcher(code="File Download", modos=["extraer"])
    madre = Resource(name="crawler", fetcher=wt, parent_resource_id=None)
    hijo = Resource(name="hijo", fetcher=wt, parent_resource_id=__import__("uuid").uuid4())
    normal = Resource(name="csv", fetcher=fd, parent_resource_id=None)
    assert madre.es_coleccion is True      # nave nodriza
    assert hijo.es_coleccion is False      # miembro promovido, no madre
    assert normal.es_coleccion is False    # especie que no descubre
