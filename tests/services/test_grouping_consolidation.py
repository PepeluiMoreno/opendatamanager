"""El inferer no debe ahogarse en portales documentales: consolida hermanas por
átomo genérico y distingue serie (dataset periódico) de pila (carpeta-bundle)."""
from app.services.grouping.inferer import infer


def _u(path):
    return {"url": "https://x.es" + path, "file_type": path.rsplit(".", 1)[-1].lower()}


def test_colapsa_numeros_de_resolucion_en_un_code():
    hojas = [_u(f"/eco/{y}/mods/{y}-{n:03d}_Resolucion.pdf")
             for y in (2022, 2023, 2024) for n in (2, 4, 5, 8)]
    props = infer(hojas)
    # No una propuesta por número: a lo sumo un puñado, con dimensión genérica
    assert len(props) <= 3
    assert any("{code}" in p.path_template or p.path_template.endswith("{*}") for p in props)


def test_serie_periodica_se_conserva_suelta():
    hojas = [_u(f"/eco/deuda/{y}/pmp/Informe_PMP_{y}_{m:02d}.xlsx")
             for y in (2023, 2024) for m in range(1, 13)]
    props = infer(hojas)
    serie = [p for p in props if not p.path_template.endswith("{*}")]
    assert any("month" in [d["kind"] for d in p.dimensions] for p in serie)


def test_carpeta_vertedero_colapsa_en_bundle():
    # 40 documentos heterogéneos solo-anuales bajo la misma carpeta → un bundle
    hojas = [_u(f"/eco/cuentas/{y}/{a:02d}-{b:02d}.pdf")
             for y in (2021, 2022, 2023) for a in range(1, 7) for b in range(1, 8)]
    props = infer(hojas)
    bundles = [p for p in props if p.path_template.endswith("{*}")]
    assert len(bundles) >= 1
    assert len(props) <= 5  # no cientos
