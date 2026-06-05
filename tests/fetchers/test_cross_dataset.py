"""Tests del núcleo puro de CruceDatasets (app.fetchers.cross_dataset.cruzar)."""
from app.fetchers.cross_dataset import cruzar

ORGANOS = [
    {"id": 2993, "descripcion": "AYUNTAMIENTO DE MADRID"},
    {"id": 3368, "descripcion": "CABILDO DE LA PALMA"},
    {"id": 9999, "descripcion": "SIN PAREJA"},
]
PUENTE = [
    {"dir3": "L01280796", "tipoAdmon": "L", "ids": [2993]},
    {"dir3": "L01380435", "tipoAdmon": "L", "ids": [3368, 3369]},
]


def test_enrich_in_array_conserva_sin_pareja():
    filas = cruzar(ORGANOS, PUENTE, left_key="id", right_key="ids",
                   match="in_array", join="enrich", select={"dir3": "dir3"})
    assert len(filas) == 3
    por_id = {f["id"]: f for f in filas}
    assert por_id[2993]["dir3"] == "L01280796"
    assert por_id[3368]["dir3"] == "L01380435"  # segundo elemento del array también indexa
    assert "dir3" not in por_id[9999]
    assert por_id[9999]["descripcion"] == "SIN PAREJA"


def test_inner_descarta_sin_pareja():
    filas = cruzar(ORGANOS, PUENTE, left_key="id", right_key="ids",
                   match="in_array", join="inner")
    assert {f["id"] for f in filas} == {2993, 3368}


def test_select_por_defecto_vuelca_todo_menos_la_clave():
    filas = cruzar(ORGANOS[:1], PUENTE, left_key="id", right_key="ids", match="in_array")
    assert filas[0]["dir3"] == "L01280796"
    assert filas[0]["tipoAdmon"] == "L"
    assert "ids" not in filas[0]


def test_match_eq():
    left = [{"k": "a", "v": 1}, {"k": "b", "v": 2}]
    right = [{"k": "a", "extra": "X"}]
    filas = cruzar(left, right, left_key="k", right_key="k", join="enrich")
    assert filas[0]["extra"] == "X"
    assert "extra" not in filas[1]
