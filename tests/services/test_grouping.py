"""
Tests del servicio de inferencia de agrupaciones.

Casos cubiertos:
  - Jerez Transparencia: grupos típicos (PMP mensual, Morosidad trimestral,
    Deuda anual, Presupuestos anuales) deben emerger sin listas de ruido.
  - Prefijo común se calcula automáticamente (no se filtra por hardcoded list).
  - path_root override sobreescribe el prefijo calculado.
  - URLs con año en filename pero no en path se agrupan por filename templatizado.
  - URLs sin estructura (ni constantes ni dimensiones) se descartan.
  - Lista vacía / URLs inválidas no rompen.
"""

from __future__ import annotations

import pytest

from app.services.grouping import infer, GroupingProposal


# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────

JEREZ_BASE = (
    "https://transparencia.jerez.es/fileadmin/Documentos/Transparencia/"
    "a-infopublica/a07-economica"
)


def _leaf(url: str, file_type: str | None = None) -> dict:
    if file_type is None:
        ext = url.rsplit(".", 1)[-1].lower()
        file_type = ext if ext in {"pdf", "xlsx", "xls", "csv"} else "unknown"
    return {"url": url, "file_type": file_type}


@pytest.fixture
def jerez_dump() -> list[dict]:
    """Dump representativo de URLs hoja descubiertas en transparencia.jerez.es.

    Estructura real (verificada contra las URLs de los seeds PDF_TABLE existentes):
      .../c-deuda/{year}/pmp/Informe_PMP_{year}_{month}.pdf      mensual
      .../c-deuda/{year}/morosidad/Informe_Ta_..._{year}-{q}.pdf trimestral
      .../c-deuda/{year}/deuda/DEUDA_FINANCIERA_31-12-{year}.pdf anual
      .../b-presupuesto/{year}/Presupuesto.xlsx                  anual
    """
    urls = []
    # PMP mensual 2022-2024 (3 años × 12 meses = 36 ficheros)
    for year in (2022, 2023, 2024):
        for month in range(1, 13):
            urls.append(
                f"{JEREZ_BASE}/c-deuda/{year}/pmp/Informe_PMP_{year}_{month:02d}.pdf"
            )
    # Morosidad trimestral 2022-2024 (3 años × 4 trimestres = 12 ficheros)
    for year in (2022, 2023, 2024):
        for q in range(1, 5):
            urls.append(
                f"{JEREZ_BASE}/c-deuda/{year}/morosidad/"
                f"Informe_Ta_Ley_15_10-{year}-T{q}.pdf"
            )
    # Deuda Financiera anual 2020-2024 (5 ficheros)
    for year in (2020, 2021, 2022, 2023, 2024):
        urls.append(
            f"{JEREZ_BASE}/c-deuda/{year}/deuda/DEUDA_FINANCIERA_31-12-{year}.pdf"
        )
    # Presupuesto anual XLSX 2021-2024 (4 ficheros)
    for year in (2021, 2022, 2023, 2024):
        urls.append(
            f"{JEREZ_BASE}/b-presupuesto/{year}/Presupuesto.xlsx"
        )
    return [_leaf(u) for u in urls]


# ──────────────────────────────────────────────────────────────────────
# Casos base
# ──────────────────────────────────────────────────────────────────────

def test_empty_input_returns_empty():
    assert infer([]) == []


def test_invalid_urls_are_skipped():
    leaves = [{"url": ""}, {"url": None}, {}, {"url": "not-a-url"}]
    # Ninguna debería romper; no producen propuestas
    assert infer(leaves) == []


# ──────────────────────────────────────────────────────────────────────
# Jerez: 4 grupos esperados, sin listas de ruido
# ──────────────────────────────────────────────────────────────────────

def test_jerez_produces_four_distinct_groups(jerez_dump):
    proposals = infer(jerez_dump)
    # PMP, Morosidad, Deuda, Presupuesto — exactamente 4
    assert len(proposals) == 4, [p.path_template for p in proposals]


def test_jerez_pmp_group(jerez_dump):
    proposals = infer(jerez_dump)
    pmp = next((p for p in proposals if "/pmp/" in p.path_template), None)
    assert pmp is not None
    assert len(pmp.matched_urls) == 36  # 3 años × 12 meses
    dim_kinds = {d["kind"] for d in pmp.dimensions}
    assert "year" in dim_kinds
    assert "month" in dim_kinds
    assert "{year}" in pmp.path_template
    assert "{month}" in pmp.path_template
    # year-in-filename también detectado en Informe_PMP_{year}_{month}.pdf
    assert pmp.suggested_name  # no vacío


def test_jerez_morosidad_group(jerez_dump):
    proposals = infer(jerez_dump)
    moro = next((p for p in proposals if "morosidad" in p.path_template), None)
    assert moro is not None
    assert len(moro.matched_urls) == 12  # 3 años × 4 trimestres
    dim_kinds = {d["kind"] for d in moro.dimensions}
    assert "year" in dim_kinds


def test_jerez_deuda_anual_group(jerez_dump):
    proposals = infer(jerez_dump)
    deuda = next(
        (p for p in proposals if "/deuda/DEUDA" in p.path_template or
         "/deuda/{" in p.path_template),
        None,
    )
    assert deuda is not None, [p.path_template for p in proposals]
    assert len(deuda.matched_urls) == 5
    dim_kinds = {d["kind"] for d in deuda.dimensions}
    assert "year" in dim_kinds


def test_jerez_presupuesto_group(jerez_dump):
    proposals = infer(jerez_dump)
    pres = next((p for p in proposals if "presupuesto" in p.path_template.lower()), None)
    assert pres is not None
    assert len(pres.matched_urls) == 4
    assert pres.file_types.get("xlsx") == 4


def test_jerez_path_template_contains_common_prefix(jerez_dump):
    """El path_template debe incluir el prefijo común (fileadmin/Documentos/...)
    para que sea reconstruible y trazable, no sólo la parte variable."""
    proposals = infer(jerez_dump)
    for p in proposals:
        assert "/fileadmin/Documentos/Transparencia/a-infopublica/a07-economica/" in p.path_template


def test_jerez_suggested_names_no_admin_noise(jerez_dump):
    """suggested_name no debe contener 'fileadmin', 'Documentos', etc.
    El filtro de naming.py los retira."""
    proposals = infer(jerez_dump)
    for p in proposals:
        low = p.suggested_name.lower()
        assert "fileadmin" not in low
        assert "documentos" not in low
        assert "transparencia" not in low
        assert "infopublica" not in low


# ──────────────────────────────────────────────────────────────────────
# path_root override
# ──────────────────────────────────────────────────────────────────────

def test_path_root_override_short(jerez_dump):
    """Forzar un prefijo más corto produce más constantes en el template."""
    proposals = infer(jerez_dump, path_root="/fileadmin/Documentos")
    # Sigue dando 4 grupos
    assert len(proposals) == 4
    # Pero el path_template debe arrancar tras /fileadmin/Documentos/
    for p in proposals:
        assert "/fileadmin/Documentos/Transparencia/a-infopublica/" in p.path_template


def test_path_root_override_specific(jerez_dump):
    """path_root muy específico funciona cuando coincide con el prefijo real."""
    proposals = infer(
        jerez_dump,
        path_root="/fileadmin/Documentos/Transparencia/a-infopublica/a07-economica/c-deuda",
    )
    # Sólo 3 grupos (los que están bajo c-deuda); el de presupuesto no encaja
    # y queda sin agrupar (o se descarta) porque no comparte el prefijo forzado.
    deuda_groups = [p for p in proposals if "c-deuda" in p.path_template]
    assert len(deuda_groups) == 3


# ──────────────────────────────────────────────────────────────────────
# Cálculo de prefijo común
# ──────────────────────────────────────────────────────────────────────

def test_common_prefix_auto_detection_two_branches():
    """Si las URLs tienen ramas distintas pero comparten un tronco,
    el prefijo se detiene en la divergencia."""
    leaves = [
        _leaf("https://example.com/data/2024/file.csv"),
        _leaf("https://example.com/data/2023/file.csv"),
        _leaf("https://example.com/reports/2024/file.csv"),
    ]
    proposals = infer(leaves)
    # /data/{year}/file.csv  y  /reports/{year}/file.csv → 2 grupos
    assert len(proposals) == 2


def test_no_common_prefix_still_groups():
    """URLs sin prefijo común se siguen agrupando por su template (post-tokenize)."""
    leaves = [
        _leaf("https://a.com/2024/x.pdf"),
        _leaf("https://a.com/2023/x.pdf"),
    ]
    proposals = infer(leaves)
    assert len(proposals) == 1
    assert "{year}" in proposals[0].path_template


# ──────────────────────────────────────────────────────────────────────
# Edge cases
# ──────────────────────────────────────────────────────────────────────

def test_url_with_year_only_in_filename():
    leaves = [
        _leaf("https://a.com/reports/Annual-2022.pdf"),
        _leaf("https://a.com/reports/Annual-2023.pdf"),
        _leaf("https://a.com/reports/Annual-2024.pdf"),
    ]
    proposals = infer(leaves)
    assert len(proposals) == 1
    p = proposals[0]
    assert "Annual-{year}.pdf" in p.path_template
    assert any(d["in_filename"] for d in p.dimensions)


def test_singleton_url_with_constant_path_kept():
    """Una URL única con segmentos constantes se mantiene como propuesta."""
    leaves = [_leaf("https://a.com/section/sub/file.pdf")]
    proposals = infer(leaves)
    assert len(proposals) == 1


def test_proposals_sorted_by_confidence_desc():
    """Las propuestas deben venir ordenadas por confianza descendente."""
    leaves = (
        # Grupo A: 5 URLs con dim tipada (alta confianza)
        [_leaf(f"https://a.com/group_a/{y}/x.csv") for y in (2020, 2021, 2022, 2023, 2024)]
        +
        # Grupo B: 1 URL singleton (baja confianza)
        [_leaf("https://a.com/group_b/standalone.pdf")]
    )
    proposals = infer(leaves)
    assert len(proposals) == 2
    assert proposals[0].confidence >= proposals[1].confidence
    assert "group_a" in proposals[0].path_template


def test_grouping_proposal_is_dataclass():
    """Verificar el shape del output."""
    leaves = [_leaf(f"https://a.com/section/{y}/file.csv") for y in (2022, 2023, 2024)]
    proposals = infer(leaves)
    assert len(proposals) == 1
    p = proposals[0]
    assert isinstance(p, GroupingProposal)
    d = p.to_dict()
    assert set(d.keys()) == {
        "path_template", "dimensions", "matched_urls",
        "file_types", "suggested_name", "confidence",
    }
