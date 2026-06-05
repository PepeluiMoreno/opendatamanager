"""Registro de estrategias de paginación (categoría de variación, puro)."""
from app.fetchers.pagination import build


def _drive(strat, batches, metas=None):
    """Simula el bucle: alimenta tamaños de lote (y metas) y recoge las peticiones."""
    metas = metas or [{}] * len(batches)
    reqs = [strat.first()]
    for size, meta in zip(batches, metas):
        nxt = strat.following(last_batch_size=size, meta=meta)
        if nxt is None:
            break
        reqs.append(nxt)
    return reqs


def test_none_una_sola_peticion():
    s = build("none", "http://x", {})
    assert _drive(s, [5]) == [{"url": "http://x", "query": {}}]


def test_query_offset_avanza_hasta_pagina_incompleta():
    s = build("query_offset", "http://x", {"page_size": 100})
    reqs = _drive(s, [100, 100, 30])  # 3ª página incompleta → fin
    offsets = [r["query"]["start_index"] for r in reqs]
    assert offsets == [0, 100, 200]


def test_query_offset_respeta_max_pages():
    s = build("query_offset", "http://x", {"page_size": 50, "max_pages": 2})
    reqs = _drive(s, [50, 50, 50])
    assert len(reqs) == 2


def test_page_number_para_en_vacio():
    s = build("page_number", "http://x", {"page_size": 10})
    reqs = _drive(s, [10, 0])
    pages = [r["query"]["page"] for r in reqs]
    assert pages == [1, 2]


def test_rel_next_sigue_enlace_y_para_sin_el():
    s = build("rel_next", "http://x", {})
    reqs = _drive(s, [30, 30, 30],
                  metas=[{"next_link": "http://x/1"}, {"next_link": "http://x/2"}, {}])
    urls = [r["url"] for r in reqs]
    assert urls == ["http://x", "http://x/1", "http://x/2"]


def test_cursor_reenvia_token():
    s = build("cursor", "http://x", {})
    reqs = _drive(s, [10, 10], metas=[{"next_cursor": "abc"}, {}])
    assert reqs[1]["query"] == {"cursor": "abc"}


def test_pivot_loop_una_peticion_por_valor():
    s = build("pivot_loop", "http://x", {"pivot_param": "prov", "pivot_values": "A,B,C"})
    reqs = _drive(s, [5, 5, 5])
    assert [r["query"]["prov"] for r in reqs] == ["A", "B", "C"]
