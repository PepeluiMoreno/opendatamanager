"""Registro de extracción HTML (dialecto de selectores, puro)."""
from app.fetchers.html_extraction import extract_html


def test_fields_por_fila():
    html = """<ul>
      <li class='r'><a href='/1'>Uno</a></li>
      <li class='r'><a href='/2'>Dos</a></li>
    </ul>"""
    out = extract_html("fields", html, {
        "rows_selector": "li.r",
        "field_selectors": {"nombre": "a"},
        "field_attr_selectors": {"url": {"selector": "a", "attr": "href"}},
    })
    assert out == [{"nombre": "Uno", "url": "/1"}, {"nombre": "Dos", "url": "/2"}]


def test_fields_documento_unico_con_all_y_label():
    html = """<div>
      <span class='tag'>a</span><span class='tag'>b</span>
      <strong>Email</strong> <span>x@y.z</span>
    </div>"""
    out = extract_html("fields", html, {
        "field_all_selectors": {"tags": ".tag"},
        "field_all_separator": ",",
        "field_label_selectors": {"email": {"container": "div", "label": "Email"}},
    })
    assert out == [{"tags": "a,b", "email": "x@y.z"}]


def test_table_con_cabecera():
    html = """<table>
      <tr><th>Provincia</th><th>Total</th></tr>
      <tr><td>Cádiz</td><td>10</td></tr>
      <tr><td>Sevilla</td><td>20</td></tr>
    </table>"""
    out = extract_html("table", html, {})
    assert out == [{"Provincia": "Cádiz", "Total": "10"},
                   {"Provincia": "Sevilla", "Total": "20"}]


def test_field_selectors_acepta_json_string():
    html = "<div><h1>Título</h1></div>"
    out = extract_html("fields", html, {"field_selectors": '{"t": "h1"}'})
    assert out == [{"t": "Título"}]


def test_fields_superset_attrs_y_all_text():
    html = "<li class='r' data-id='42'><span class='t'>a</span><span class='t'>b</span></li>"
    out = extract_html("fields", html, {
        "rows_selector": "li.r",
        "field_attrs": {"id": "data-id"},
        "field_all_text": {"tags": ".t"},
        "field_all_separator": "+",
    })
    assert out == [{"id": "42", "tags": "a+b"}]
