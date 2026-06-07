"""Tests de carve_tabular_series: capacidad genérica del inferer que rescata las
hojas tabulares (xlsx/csv/tsv…) sepultadas en bundles mixtos con prosa.

Sin conocimiento de ningún portal: URLs sintéticas neutras.
"""
from __future__ import annotations

from app.services.grouping import GroupingProposal, carve_tabular_series, infer

BASE = "https://datos.example.gov/eco"


def test_carva_xlsx_sepultado_en_bundle_mixto():
    leaves = [
        {"url": f"{BASE}/2023/varios/decreto.pdf", "file_type": "pdf"},
        {"url": f"{BASE}/2023/varios/tabla.xlsx", "file_type": "xlsx"},
        {"url": f"{BASE}/2024/varios/decreto.pdf", "file_type": "pdf"},
        {"url": f"{BASE}/2024/varios/tabla.xlsx", "file_type": "xlsx"},
    ]
    mixto = GroupingProposal(
        path_template=f"{BASE}/{{*}}",
        matched_urls=[h["url"] for h in leaves],
        file_types={"pdf": 2, "xlsx": 2},
        suggested_name="varios (bundle)",
        confidence=0.3,
    )
    nuevas = carve_tabular_series(leaves, [mixto])
    carved = {u for p in nuevas for u in p.matched_urls}
    assert nuevas, "debe rescatar el xlsx sepultado"
    assert any(u.endswith("tabla.xlsx") for u in carved)
    assert all(not u.endswith("decreto.pdf") for u in carved), "la prosa no se carva"


def test_noop_cuando_la_serie_tabular_ya_esta_limpia():
    leaves = [
        {"url": f"{BASE}/2023/datos.xlsx", "file_type": "xlsx"},
        {"url": f"{BASE}/2024/datos.xlsx", "file_type": "xlsx"},
    ]
    props = infer(leaves)  # una serie íntegramente xlsx
    assert carve_tabular_series(leaves, props) == []


def test_noop_sin_hojas_tabulares():
    leaves = [
        {"url": f"{BASE}/2023/x/a.pdf", "file_type": "pdf"},
        {"url": f"{BASE}/2024/x/a.pdf", "file_type": "pdf"},
    ]
    props = infer(leaves)
    assert carve_tabular_series(leaves, props) == []


def test_formato_se_deriva_de_la_extension_si_falta_file_type():
    # sin file_type: el formato sale del path de la URL
    leaves = [
        {"url": f"{BASE}/2023/x/a.pdf"},
        {"url": f"{BASE}/2023/x/b.csv"},
        {"url": f"{BASE}/2024/x/a.pdf"},
        {"url": f"{BASE}/2024/x/b.csv"},
    ]
    mixto = GroupingProposal(
        path_template=f"{BASE}/{{*}}",
        matched_urls=[h["url"] for h in leaves],
        file_types={"unknown": 4},
        suggested_name="x (bundle)",
        confidence=0.3,
    )
    nuevas = carve_tabular_series(leaves, [mixto])
    carved = {u for p in nuevas for u in p.matched_urls}
    assert any(u.endswith("b.csv") for u in carved)
    assert all(not u.endswith("a.pdf") for u in carved)
