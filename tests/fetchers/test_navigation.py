"""Registro de navegación HTML (helpers puros)."""
from app.fetchers.navigation import pivot_values, build_url, paged_urls, next_link, follow_links


def test_pivot_values_lista_json_y_csv():
    assert pivot_values({"pivot_values": ["a", "b"]}) == ["a", "b"]
    assert pivot_values({"search_field_values": '["01","02"]'}) == ["01", "02"]
    assert pivot_values({"pivot_values": "x, y ,z"}) == ["x", "y", "z"]
    assert pivot_values({}) == []


def test_build_url_y_paged():
    assert build_url("h/{value}/p?n={page}", value="ca", page=2) == "h/ca/p?n=2"
    assert build_url("h/{value}", value="ca") == "h/ca"  # {page} ausente, intacto si no se pasa
    assert paged_urls("h?p={page}", None, 1, 3) == ["h?p=1", "h?p=2", "h?p=3"]


def test_next_link_lista_selectores_y_urljoin():
    html = "<div><a class='nope'>x</a><a rel='next' href='/p/2'>sig</a></div>"
    assert next_link(html, ["a.foo", "a[rel=next]"], base_url="https://e.org/p/1") == "https://e.org/p/2"
    assert next_link("<div></div>", "a[rel=next]") is None


def test_follow_links():
    html = "<ul><a class='sub' href='/a'>A</a><a class='sub' href='/b'>B</a></ul>"
    assert follow_links(html, "a.sub", base_url="https://e.org") == ["https://e.org/a", "https://e.org/b"]


def test_form_next_extrae_inputs_e_incrementa_pagina():
    from app.fetchers.navigation import form_next
    html = """<form name='paginationForm' action='/Maper/buscarRER.action'>
      <input type='hidden' name='token' value='abc'/>
      <input type='hidden' name='pagina' value='3'/>
      <select name='orden'><option value='nombre' selected>n</option></select>
    </form>"""
    destino, inputs = form_next(html, "form[name='paginationForm'], .paginacion-form",
                                page_param="pagina", base_url="https://maper.mjusticia.gob.es/Maper/RER.action")
    assert destino == "https://maper.mjusticia.gob.es/Maper/buscarRER.action"
    assert inputs["token"] == "abc" and inputs["pagina"] == "4" and "orden" in inputs
    assert form_next("<div>sin formulario</div>", "form") is None
