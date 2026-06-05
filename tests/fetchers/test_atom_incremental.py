"""Parada incremental por fecha del AtomFetcher (helpers puros)."""
from datetime import datetime
from app.fetchers.atom import _parse_dt, _filtrar_por_fecha


def test_parse_dt_varios_formatos():
    assert _parse_dt("2026-06-05T10:00:00+02:00").year == 2026
    assert _parse_dt("2026-06-05T10:00:00Z").hour == 10
    assert _parse_dt("2026-06-05").day == 5
    assert _parse_dt(None) is None
    assert _parse_dt("no-fecha") is None


def test_filtra_y_detecta_frontera():
    desde = datetime(2026, 6, 1)
    batch = [
        {"fecha": "2026-06-04T09:00:00+02:00"},  # >= desde → se queda
        {"fecha": "2026-06-02"},                  # >= desde → se queda
        {"fecha": "2026-05-30"},                  # < desde → frontera
        {"fecha": "2026-05-29"},                  # < desde
    ]
    kept, frontera = _filtrar_por_fecha(batch, "fecha", desde)
    assert len(kept) == 2
    assert frontera is True


def test_sin_desde_no_filtra():
    batch = [{"fecha": "2020-01-01"}, {"fecha": "2026-06-01"}]
    kept, frontera = _filtrar_por_fecha(batch, "fecha", None)
    assert len(kept) == 2 and frontera is False


def test_entradas_sin_fecha_no_se_descartan():
    desde = datetime(2026, 6, 1)
    batch = [{"otro": "x"}, {"fecha": "2026-06-03"}]
    kept, frontera = _filtrar_por_fecha(batch, "fecha", desde)
    assert len(kept) == 2 and frontera is False


def test_aware_vs_naive_no_rompe():
    desde = datetime(2026, 6, 1)
    kept, frontera = _filtrar_por_fecha([{"fecha": "2026-06-05T00:00:00+02:00"}], "fecha", desde)
    assert len(kept) == 1
