"""Tests del servicio de taxonomía (puros, sin BD)."""
from app.services.taxonomia import segmentos_constantes, construir_taxonomia


def test_segmentos_constantes_ignora_placeholders():
    p = "https://x.es/raiz/a06-contratos/b-convenios/{year}/urbanismo/{*}"
    assert segmentos_constantes(p) == ["raiz", "a06-contratos", "b-convenios", "urbanismo"]


def test_segmentos_constantes_path_vacio():
    assert segmentos_constantes("") == []
    assert segmentos_constantes("https://x.es/") == []


def _item(id, path, urls=1, ft=None, dims=("year",)):
    return {
        "id": id,
        "path_template": path,
        "matched_urls": [f"{id}_u{i}" for i in range(urls)],
        "file_types": ft or {"pdf": urls},
        "dimensions": [{"kind": d} for d in dims],
        "suggested_name": id,
    }


def _by_path(arbol):
    return {n["path"]: n for n in arbol}


def test_ramificacion_y_colapso():
    items = [
        _item("c1", "https://x/p/a06-contratos/b-convenios/{year}/urbanismo/{*}", urls=2),
        _item("c2", "https://x/p/a06-contratos/b-convenios/{year}/empleo/{*}", urls=1),
        _item("c3", "https://x/p/a07-economica/a-presupuesto/{year}/{*}", urls=3, ft={"xlsx": 3}),
    ]
    nodos = _by_path(construir_taxonomia(items))

    # La rama común de los dos convenios existe y agrega ambos.
    conv = nodos["p/a06-contratos/b-convenios"]
    assert conv["num_candidatos"] == 2
    assert conv["num_directos"] == 0          # los directos cuelgan de urbanismo/empleo
    assert conv["num_urls"] == 3              # 2 + 1
    assert conv["label"] == "a06-contratos/b-convenios"  # 'p' es raíz; a06 se colapsa con b-convenios

    # Las hojas llevan el candidato directo promovible.
    urb = nodos["p/a06-contratos/b-convenios/urbanismo"]
    assert urb["candidato_ids"] == ["c1"] and urb["num_directos"] == 1

    # La rama económica es independiente y arrastra su propio formato/dimensión.
    eco = nodos["p/a07-economica/a-presupuesto"]
    assert eco["num_candidatos"] == 1 and eco["num_urls"] == 3
    assert eco["formatos"] == {"xlsx": 3}
    assert eco["dimensiones"] == ["year"]


def test_agregados_dimensiones_se_unen():
    items = [
        _item("c1", "https://x/raiz/seccion/serieA/{year}/{*}", urls=5, dims=("year",)),
        _item("c2", "https://x/raiz/seccion/serieB/{month}/{*}", urls=5, dims=("month",)),
    ]
    nodos = _by_path(construir_taxonomia(items))
    sec = nodos["raiz/seccion"]
    assert sec["num_candidatos"] == 2
    assert sec["dimensiones"] == ["month", "year"]   # unión ordenada
    assert sec["num_urls"] == 10


def test_raiz_presente_y_total():
    items = [_item("c1", "https://x/a/b/{year}/{*}", urls=4)]
    arbol = construir_taxonomia(items)
    raiz = next(n for n in arbol if n["parent"] is None)
    assert raiz["num_candidatos"] == 1
    assert raiz["num_urls"] == 4


from app.services.taxonomia import fundir_rama


def test_fundir_rama_deriva_dimension_del_segmento_variable():
    # Tres hojas bajo .../b-convenios/{year}/<tipo>/{*} — el tipo varía.
    items = [
        _item("c1", "https://x/p/a06-contratos/b-convenios/{year}/urbanismo/{*}", urls=2),
        _item("c2", "https://x/p/a06-contratos/b-convenios/{year}/empleo/{*}", urls=3),
        _item("c3", "https://x/p/a06-contratos/b-convenios/{year}/igualdad/{*}", urls=1),
    ]
    fus = fundir_rama(items)
    assert len(fus) == 1                       # misma forma -> una sola fusión
    f = fus[0]
    assert f["num_hojas"] == 3
    assert len(f["matched_urls"]) == 6         # 2+3+1, sin duplicar
    # El segmento que varía se abre como dimensión derivada.
    assert f["path_template"].endswith("/b-convenios/{year}/{rama1}/{*}")
    derivadas = [d for d in f["dimensions"] if d["kind"] == "branch"]
    assert len(derivadas) == 1
    assert derivadas[0]["sample_values"] == ["empleo", "igualdad", "urbanismo"]
    # La dimensión original (year) se conserva.
    assert any(d.get("kind") == "year" for d in f["dimensions"])


def test_fundir_rama_separa_formas_distintas():
    items = [
        _item("c1", "https://x/p/sec/serieA/{year}/{*}", urls=2),
        _item("c2", "https://x/p/sec/serieB/{year}/sub/{*}", urls=2),  # un segmento más
    ]
    fus = fundir_rama(items)
    assert len(fus) == 2                       # formas incompatibles -> dos fusiones


def test_fundir_rama_constante_comun_no_es_dimension():
    items = [
        _item("c1", "https://x/p/sec/{year}/{*}", urls=4),
        _item("c2", "https://x/p/sec/{year}/{*}", urls=2),
    ]
    fus = fundir_rama(items)
    assert len(fus) == 1
    assert not [d for d in fus[0]["dimensions"] if d["kind"] == "branch"]
    assert len(fus[0]["matched_urls"]) == 6
