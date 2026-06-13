"""Tests del modo DESCUBRIR de SearchLoopHtmlFetcher.propose():
emisión de hijos heterogéneos (p. ej. Web Tree) sembrados por una URL
extraída de cada registro. Sin red: se monkeypatchea fetch()."""
from app.fetchers.searchloop_html import SearchLoopHtmlFetcher


def _fetcher(params, records):
    f = SearchLoopHtmlFetcher(params)
    f.fetch = lambda: records  # type: ignore  # evita la red
    return f


def test_propose_siembra_web_tree_por_url():
    records = [
        {"nombre": "Diócesis de Jerez", "web": "https://www.diocesisdejerez.org/"},
        {"nombre": "Diócesis de Bilbao", "web": "https://www.bizkeliza.org"},
    ]
    f = _fetcher({
        "root_url_from_field": "web",
        "child_fetcher": "Web Tree",
        "child_name_field": "nombre",
        "child_params": '{"file_extensions": "pdf,csv", "max_depth": "2"}',
    }, records)
    props = f.propose()
    assert len(props) == 2
    p0 = props[0]
    assert p0["target_fetcher_code"] == "Web Tree"
    assert p0["target_params"]["root_url"] == "https://www.diocesisdejerez.org/"
    assert p0["target_params"]["file_extensions"] == "pdf,csv"
    assert p0["suggested_name"] == "Diócesis de Jerez"
    # normaliza barra final
    assert props[1]["target_params"]["root_url"].endswith("/")


def test_propose_dedup_y_filtra_no_http():
    records = [
        {"nombre": "A", "web": "https://a.org/"},
        {"nombre": "A duplicada", "web": "https://a.org"},   # mismo destino normalizado
        {"nombre": "Sin web", "web": ""},
        {"nombre": "Relativa", "web": "/transparencia"},      # no http → descartada
    ]
    f = _fetcher({"root_url_from_field": "web"}, records)
    props = f.propose()
    assert len(props) == 1
    assert props[0]["target_fetcher_code"] == "Web Tree"  # default


def test_sin_root_url_from_field_no_propone():
    """Retro-compatibilidad: sin el parámetro, sigue siendo extractor puro."""
    f = _fetcher({}, [{"nombre": "X", "web": "https://x.org"}])
    assert f.propose() == []
