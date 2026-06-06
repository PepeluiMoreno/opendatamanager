"""Modo censo: una fila por fichero, sin descargar nada (URLs falsas a propósito:
si intentara descargar, fallaría)."""
from app.fetchers.web_tree_fetcher import WebTreeFetcher

URLS = [f"https://inexistente.example/eco/{y}/doc_{i}.pdf" for y in (2023, 2024) for i in range(3)]


def _fetcher(**extra):
    return WebTreeFetcher({"root_url": "https://inexistente.example",
                           "extract_mode": "censo",
                           "_matched_urls": URLS,
                           "_path_template": "https://inexistente.example/eco/{year}/{*}",
                           "_dimensions": [{"name": "year"}], **extra})


def test_censo_una_fila_por_fichero_sin_descargar():
    filas = [r for lote in _fetcher().stream() for r in lote]
    assert len(filas) == len(URLS)
    assert filas[0]["year"] == "2023" and filas[0]["_source_format"] == "pdf"
    assert filas[0]["_source_file_name"] == "doc_0.pdf"


def test_censo_respeta_preview_limit():
    filas = [r for lote in _fetcher(_preview_limit="4").stream() for r in lote]
    assert len(filas) <= 6 and len(filas) >= 4
