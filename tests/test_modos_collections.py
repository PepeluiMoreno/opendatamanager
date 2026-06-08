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
    # Web Tree madre, pero NO cualificada como generador de colecciones: solo extrae.
    extractor = Resource(name="extractor", fetcher=wt, parent_resource_id=None,
                         genera_colecciones=False)
    # Web Tree madre cualificada: nave nodriza.
    madre = Resource(name="crawler", fetcher=wt, parent_resource_id=None,
                     genera_colecciones=True)
    hijo = Resource(name="hijo", fetcher=wt, parent_resource_id=__import__("uuid").uuid4(),
                    genera_colecciones=True)
    normal = Resource(name="csv", fetcher=fd, parent_resource_id=None,
                      genera_colecciones=True)
    assert madre.es_coleccion is True       # capaz + madre + cualificada
    assert extractor.es_coleccion is False  # capaz y madre, pero NO cualificada → extrae
    assert hijo.es_coleccion is False       # miembro promovido, no madre
    assert normal.es_coleccion is False     # especie que no descubre
