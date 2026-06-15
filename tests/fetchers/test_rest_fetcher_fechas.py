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


# --- modo incremental (_watermark) + formato de fecha ------------------------
def test_watermark_a_fecha_desde_con_margen_y_formato():
    q = _fetch_capturando({
        "url": "https://api.example.com/concesiones/busqueda",
        "method": "GET",
        "query_params": {"vpd": "GE"},
        "fecha_formato": "%d/%m/%Y",
        "desde": "auto",
        "incremental_margen_dias": "30",
        "_watermark": "2026-06-14T03:00:00",   # lo inyecta el manager (desde=auto)
    })
    assert q["fechaDesde"] == "15/05/2026"   # 14/06 − 30 días, en dd/mm/yyyy
    assert "fechaHasta" not in q


def test_fecha_desde_explicito_manda_sobre_watermark():
    q = _fetch_capturando({
        "url": "https://api.example.com/x", "method": "GET",
        "fecha_formato": "%d/%m/%Y",
        "desde": "auto",
        "fecha_desde": "01/01/2024",
        "_watermark": "2026-06-14T03:00:00",
    })
    assert q["fechaDesde"] == "01/01/2024"


def test_formato_reescribe_iso_y_ddmmyyyy():
    q = _fetch_capturando({
        "url": "https://api.example.com/x", "method": "GET",
        "fecha_formato": "%d/%m/%Y",
        "fecha_desde": "2024-03-05",   # ISO → dd/mm/yyyy
        "fecha_hasta": "31/12/2024",   # ya dd/mm/yyyy → se mantiene
    })
    assert q["fechaDesde"] == "05/03/2024"
    assert q["fechaHasta"] == "31/12/2024"


def test_sin_formato_pasa_tal_cual():
    q = _fetch_capturando({
        "url": "https://api.example.com/x", "method": "GET",
        "fecha_desde": "2024-03-05",
    })
    assert q["fechaDesde"] == "2024-03-05"


def test_fallback_primera_vez_acota_carga_inicial():
    import datetime
    q = _fetch_capturando({
        "url": "https://api.example.com/x", "method": "GET",
        "desde": "auto", "fecha_formato": "%d/%m/%Y",
        "incremental_fallback_dias": "400",   # sin _watermark (1ª ejecución)
    })
    esperado = (datetime.date.today() - datetime.timedelta(days=400)).strftime("%d/%m/%Y")
    assert q["fechaDesde"] == esperado


def test_sin_desde_auto_ignora_watermark():
    q = _fetch_capturando({
        "url": "https://api.example.com/x", "method": "GET",
        "fecha_formato": "%d/%m/%Y", "incremental_margen_dias": "30",
        "_watermark": "2026-06-14T03:00:00",   # pero NO hay desde=auto
    })
    assert "fechaDesde" not in q   # sin desde=auto, el watermark no aplica
