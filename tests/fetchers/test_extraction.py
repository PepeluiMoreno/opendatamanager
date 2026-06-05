"""Registro de estrategias de extracción (categoría de variación, puro)."""
from app.fetchers.extraction import extract


def test_passthrough_lista_y_content_field():
    assert extract("passthrough", [1, 2, 3], {}) == [1, 2, 3]
    assert extract("passthrough", {"content": [{"a": 1}]}, {"content_field": "content"}) == [{"a": 1}]


def test_field_map_aplana_por_rutas():
    payload = {"data": {"items": [{"id": 1, "x": {"y": "v"}}]}}
    out = extract("field_map", payload, {"content_field": "data.items",
                                         "field_map": {"clave": "id", "val": "x.y"}})
    assert out == [{"clave": 1, "val": "v"}]


def test_field_map_sobre_lista_ya_seleccionada_idempotente():
    # payload ya es lista (modo paginado) → no re-selecciona aunque haya content_field
    out = extract("field_map", [{"id": 7}], {"content_field": "content", "field_map": {"k": "id"}})
    assert out == [{"k": 7}]


def test_bindings_sparql():
    payload = {"results": {"bindings": [{"municipio": {"value": "Cádiz"}, "n": {"value": "3"}}]}}
    assert extract("bindings", payload, {}) == [{"municipio": "Cádiz", "n": "3"}]


def test_timeseries_long():
    payload = [{
        "MetaData": [{"Variable": {"Codigo": "PROV"}, "Nombre": "Cádiz"}],
        "Data": [{"Anyo": 2025, "Valor": 10}, {"Anyo": 2026, "Valor": 12}],
    }]
    out = extract("timeseries_long", payload, {})
    assert out == [{"PROV": "Cádiz", "periodo": 2025, "valor": 10},
                   {"PROV": "Cádiz", "periodo": 2026, "valor": 12}]
