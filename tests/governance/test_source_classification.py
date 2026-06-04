"""Tests del núcleo de clasificación de origen y política de admisión."""
import app.governance.source_classification as sc


def test_clasificar_privado_siempre_scraping_privado():
    assert sc.clasificar("PRIVADO", "API REST") == sc.SCRAPING_PRIVADO
    assert sc.clasificar("PRIVADO", "URL Loop HTML") == sc.SCRAPING_PRIVADO


def test_clasificar_publico_por_fetcher():
    assert sc.clasificar("ESTATAL", "API REST") == sc.API_ABIERTA
    assert sc.clasificar("ESTATAL", "WFS") == sc.API_ABIERTA
    assert sc.clasificar("INTERNACIONAL", "OSM Overpass") == sc.PUBLICACION_ABIERTA
    assert sc.clasificar("ESTATAL", "File Download") == sc.PUBLICACION_ABIERTA
    assert sc.clasificar("ESTATAL", "HTML SearchLoop") == sc.SCRAPING_PUBLICO
    assert sc.clasificar("LOCAL", "Web Tree") == sc.SCRAPING_PUBLICO


def test_clasificar_desconocido_es_none():
    assert sc.clasificar("ESTATAL", "Fetcher Inventado") is None


def test_es_abierto():
    assert sc.es_abierto(sc.API_ABIERTA)
    assert sc.es_abierto(sc.PUBLICACION_ABIERTA)
    assert not sc.es_abierto(sc.SCRAPING_PRIVADO)
    assert not sc.es_abierto(None)


def test_politica_default_solo_abiertas(monkeypatch):
    monkeypatch.delenv("ODM_ALLOWED_SOURCE_CLASSES", raising=False)
    assert sc.admite(sc.API_ABIERTA)
    assert sc.admite(sc.PUBLICACION_ABIERTA)
    assert not sc.admite(sc.SCRAPING_PRIVADO)
    assert not sc.admite(sc.SCRAPING_PUBLICO)
    assert not sc.admite(None)


def test_politica_ampliable(monkeypatch):
    monkeypatch.setenv("ODM_ALLOWED_SOURCE_CLASSES", "api_abierta,publicacion_abierta,scraping_publico")
    assert sc.admite(sc.SCRAPING_PUBLICO)
    assert not sc.admite(sc.SCRAPING_PRIVADO)
