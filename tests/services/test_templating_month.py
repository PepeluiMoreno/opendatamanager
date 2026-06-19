"""Guard del mes numérico en template_path_segments.

Un segmento de 1-2 dígitos solo es {month} si hay un {year} más superficial en
el mismo path. Sin ese contexto se deja literal: evita que códigos de provincia
(02, 11…), gerencia o capítulo se confundan con meses —el falso positivo que
sacaba el feed del Catastro como /{month}/ en vez de la provincia.
"""
from app.services.grouping.templating import template_path_segments


def test_provincia_sin_anio_no_es_mes():
    segs, dims = template_path_segments(["INSPIRE", "CadastralParcels", "02", "02001-ABENGIBRE"])
    assert "{month}" not in segs
    assert segs[2] == "02"
    assert not any(d["kind"] == "month" for d in dims)


def test_mes_numerico_con_anio_previo_si_se_detecta():
    segs, dims = template_path_segments(["datos", "2024", "03"])
    assert segs == ["datos", "{year}", "{month}"]
    kinds = {d["kind"] for d in dims}
    assert {"year", "month"} <= kinds


def test_mes_por_nombre_sigue_siendo_inequivoco():
    # los meses por NOMBRE no necesitan año-contexto (no son ambiguos)
    segs, _ = template_path_segments(["informes", "marzo"])
    assert segs == ["informes", "{month}"]
