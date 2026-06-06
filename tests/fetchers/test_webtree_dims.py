"""Extracción de dimensiones por path_template: el caso real de Jerez que salía
year='Documentos', month='2026'."""
from app.fetchers.web_tree_fetcher import WebTreeFetcher

TPL = ("https://transparencia.jerez.es/fileadmin/Documentos/Transparencia/"
       "a-infopublica/a07-economica/c-deuda/{year}/pmp/Informe_PMP_{year}_{month}.xlsx")
URL = ("https://transparencia.jerez.es/fileadmin/Documentos/Transparencia/"
       "a-infopublica/a07-economica/c-deuda/2026/pmp/Informe_PMP_2026_01.xlsx")


def _f(tpl):
    return WebTreeFetcher({"root_url": "https://x", "_path_template": tpl})


def test_caso_real_jerez_pmp():
    dims = [{"name": "year"}, {"name": "month"}]
    out = _f(TPL)._extract_dim_values(URL, dims)
    assert out == {"year": "2026", "month": "01"}


def test_bundle_asterisco_y_code():
    tpl = "https://x.es/eco/{year}/mods/{year}-{code}_Resolucion.pdf"
    url = "https://x.es/eco/2024/mods/2024-007_Resolucion.pdf"
    out = _f(tpl)._extract_dim_values(url, [{"name": "year"}, {"name": "code"}])
    assert out == {"year": "2024", "code": "007"}
    tpl2 = "https://x.es/eco/{year}/cuentas/{*}"
    url2 = "https://x.es/eco/2023/cuentas/03-02-01.pdf"
    out2 = _f(tpl2)._extract_dim_values(url2, [{"name": "year"}])
    assert out2 == {"year": "2023"}
