"""Tests de la extensión Struts/POST del SearchLoopHtmlFetcher."""
from bs4 import BeautifulSoup
from app.fetchers.searchloop_html import SearchLoopHtmlFetcher, _as_bool


def _f(**extra):
    p = {"url": "https://x/RER.action", "search_field_name": "filtro.codigosComunidad"}
    p.update(extra)
    return SearchLoopHtmlFetcher(p)


def test_as_bool():
    assert _as_bool(True) and _as_bool("true") and _as_bool("1") and _as_bool("sí")
    assert not _as_bool(False) and not _as_bool(None) and not _as_bool("no")


def test_modo_get_por_defecto():
    m, enc, ms, ch = _f()._resolve_search_mode()
    assert (m, enc, ms, ch) == ("GET", "urlencoded", False, False)


def test_modo_struts_defaults():
    m, enc, ms, ch = _f(search_mode="POST_struts")._resolve_search_mode()
    assert m == "POST" and enc == "multipart" and ms is True and ch is True


def test_override_explicito_gana():
    # En POST_struts, pero desactivo multiselect explícitamente
    m, enc, ms, ch = _f(search_mode="POST_struts", multiselect_companion="false")._resolve_search_mode()
    assert ms is False


def test_ensure_form_state_captura_hidden_y_accion(monkeypatch):
    html = """
      <form action="/Maper/buscarRER.action;jsessionid=ABC" method="post" enctype="multipart/form-data">
        <input type="hidden" name="struts.token" value="TKN123"/>
        <select name="filtro.codigosComunidad"><option value="AN">ANDALUCIA</option></select>
      </form>"""
    fetcher = _f()
    monkeypatch.setattr(fetcher, "_fetch", lambda *a, **k: BeautifulSoup(html, "html.parser"))
    fetcher._ensure_form_state()
    assert fetcher._form_hidden == {"struts.token": "TKN123"}
    assert fetcher._discovered_action == "https://x/Maper/buscarRER.action;jsessionid=ABC"


def test_send_search_multipart_construye_files(monkeypatch):
    fetcher = _f(search_mode="POST_struts")
    captured = {}
    def fake_fetch(url, method="GET", data=None, params=None, files=None):
        captured.update(url=url, method=method, data=data, params=params, files=files)
        return BeautifulSoup("<html></html>", "html.parser")
    monkeypatch.setattr(fetcher, "_fetch", fake_fetch)
    fetcher._send_search("https://x/buscarRER.action", "POST", "multipart",
                         {"filtro.codigosComunidad": "AN", "__multiselect_filtro.codigosComunidad": ""})
    assert captured["method"] == "POST" and captured["files"] is not None
    assert captured["files"]["filtro.codigosComunidad"] == (None, "AN")
    assert "__multiselect_filtro.codigosComunidad" in captured["files"]
