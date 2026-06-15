"""Tests del intervalo temporal de runtime y el templating del RESTFetcher.

Fija el comportamiento añadido para el backfill BDNS:
  - fecha_desde/fecha_hasta (params de runtime) → query fechaDesde/fechaHasta.
  - nombres de param configurables (fecha_param_desde/fecha_param_hasta).
  - sin fechas → no se envía filtro (corpus íntegro).
  - templating {token} en los valores de query_params; token ausente → se omite.
"""
from unittest.mock import Mock, patch
from app.fetchers.rest import RestFetcher


def _fetch_capturando(params):
    """Ejecuta fetch() con pagination 'none' y devuelve el dict `params` enviado."""
    fetcher = RestFetcher({**params, "pagination": "none"})
    with patch("requests.request") as mock_request:
        resp = Mock()
        resp.text = "{}"
        resp.status_code = 200
        resp.raise_for_status = Mock()
        mock_request.return_value = resp
        fetcher.fetch()
        return mock_request.call_args.kwargs["params"]


def test_ventana_fechas_nativa():
    q = _fetch_capturando({
        "url": "https://api.example.com/concesiones/busqueda",
        "method": "GET",
        "query_params": {"vpd": "GE"},
        "fecha_desde": "01/01/2024",
        "fecha_hasta": "31/12/2024",
    })
    assert q["fechaDesde"] == "01/01/2024"
    assert q["fechaHasta"] == "31/12/2024"
    assert q["vpd"] == "GE"


def test_nombres_de_param_configurables():
    q = _fetch_capturando({
        "url": "https://api.example.com/x",
        "method": "GET",
        "fecha_param_desde": "since",
        "fecha_param_hasta": "until",
        "fecha_desde": "2024-01-01",
        "fecha_hasta": "2024-12-31",
    })
    assert q["since"] == "2024-01-01"
    assert q["until"] == "2024-12-31"
    assert "fechaDesde" not in q


def test_sin_fechas_no_envia_filtro():
    q = _fetch_capturando({
        "url": "https://api.example.com/x",
        "method": "GET",
        "query_params": {"vpd": "GE"},
    })
    assert "fechaDesde" not in q and "fechaHasta" not in q
    assert q == {"vpd": "GE"}


def test_templating_token_presente():
    q = _fetch_capturando({
        "url": "https://api.example.com/x",
        "method": "GET",
        "query_params": {"ciudad": "{ciudad}", "fijo": "1"},
        "ciudad": "Jerez",
    })
    assert q["ciudad"] == "Jerez"
    assert q["fijo"] == "1"


def test_templating_token_ausente_se_omite():
    q = _fetch_capturando({
        "url": "https://api.example.com/x",
        "method": "GET",
        "query_params": {"ciudad": "{ciudad}", "fijo": "1"},
    })
    assert "ciudad" not in q   # token sin valor → filtro omitido
    assert q["fijo"] == "1"
