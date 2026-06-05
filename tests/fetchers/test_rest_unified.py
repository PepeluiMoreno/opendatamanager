"""Helpers del RESTFetcher unificado (extracción de registros, puro)."""
from app.fetchers.rest import _dig, _extract_list


def test_dig_ruta_con_puntos():
    assert _dig({"data": {"items": [1, 2]}}, "data.items") == [1, 2]
    assert _dig({"a": 1}, "b") is None
    assert _dig([1, 2], "x") is None


def test_extract_list_con_content_field():
    assert _extract_list({"content": [1, 2, 3]}, "content") == [1, 2, 3]
    assert _extract_list({"content": "x"}, "content") == []  # no es lista → []


def test_extract_list_sin_content_field():
    assert _extract_list([1, 2], None) == [1, 2]   # página ya es lista
    assert _extract_list({"a": 1}, None) == []      # dict sin ruta → []
