"""Modo CKAN del CatalogFetcher (descubrir registros vía package_search).
Sin red: se mockea _request con páginas CKAN canónicas."""
from app.fetchers.catalog import CatalogFetcher


class _Resp:
    def __init__(self, data): self._d = data
    def raise_for_status(self): pass
    def json(self): return self._d


def _ckan_fetcher(pages):
    f = CatalogFetcher({
        "catalog_type": "ckan",
        "catalog_api": "https://portal.example",
        "query_terms": "registre associacions",
        "title_include": r"regist(re|ro)\s+.*(associaci|entitat)",
        "title_exclude": r"(juvenil|esportiv)",
        "formats": "csv",
        "page_size": "50", "max_pages": "3",
        "child_fetcher": "File Download",
    })
    seq = {"i": 0}
    def fake(_none, _method, _url, params=None, headers=None, timeout=None):
        i = seq["i"]; seq["i"] += 1
        return _Resp(pages[i] if i < len(pages) else {"success": True, "result": {"results": []}})
    f._request = fake
    return f


def test_ckan_descubre_y_filtra():
    page = {"success": True, "result": {"results": [
        {"title": "Registre municipal d'associacions",
         "organization": {"title": "Ajuntament de Test"},
         "resources": [{"url": "https://x/test/assoc.csv", "format": "CSV", "name": "assoc"}]},
        {"title": "Associacions juvenils",   # excluida por title_exclude
         "organization": {"title": "X"},
         "resources": [{"url": "https://x/juv.csv", "format": "CSV"}]},
        {"title": "Pressupost municipal",     # no casa include
         "organization": {"title": "Y"},
         "resources": [{"url": "https://x/preu.csv", "format": "CSV"}]},
    ]}}
    f = _ckan_fetcher([page])
    props = f.propose()
    assert len(props) == 1
    p = props[0]
    assert p["target_fetcher_code"] == "File Download"
    assert p["target_params"] == {"url": "https://x/test/assoc.csv", "format": "csv"}
    assert "Ajuntament de Test" in p["suggested_name"]


def test_ckan_respeta_formats_y_drop():
    page = {"success": True, "result": {"results": [
        {"title": "Registre d'entitats",
         "organization": {"title": "Aj"},
         "resources": [
             {"url": "https://x/diccionario.csv", "format": "CSV"},   # drop por defecto
             {"url": "https://x/entitats.json", "format": "JSON"},    # formato no admitido
             {"url": "https://x/entitats.csv", "format": "CSV"},      # ✓
         ]},
    ]}}
    f = _ckan_fetcher([page])
    props = f.propose()
    urls = [p["target_params"]["url"] for p in props]
    assert urls == ["https://x/entitats.csv"]
