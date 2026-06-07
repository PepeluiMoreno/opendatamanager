"""Tests de las funciones puras de manifiestos (sin BD)."""
from types import SimpleNamespace as NS

from app.services.manifests import validate_manifest, build_manifest, MANIFEST_VERSION

KNOWN = {"API REST", "File Download", "OSM Overpass"}


def _ok_manifest():
    return {
        "odm_manifest_version": 1,
        "publisher": {"acronimo": "INE", "nombre": "Instituto Nacional de Estadística", "nivel": "ESTATAL"},
        "resources": [{
            "name": "España - Municipios (INE)",
            "fetcher": "API REST",
            "schedule": "0 4 1 1 *",
            "active": True,
            "params": [{"key": "url", "value": "https://x", "is_external": False}],
        }],
    }


def test_manifest_valido():
    assert validate_manifest(_ok_manifest(), KNOWN) == []


def test_version_incorrecta():
    m = _ok_manifest(); m["odm_manifest_version"] = 2
    assert any("odm_manifest_version" in e for e in validate_manifest(m, KNOWN))


def test_falta_publisher_acronimo():
    m = _ok_manifest(); m["publisher"] = {"nombre": "x"}
    assert any("publisher.acronimo" in e for e in validate_manifest(m, KNOWN))


def test_fetcher_no_registrado():
    m = _ok_manifest(); m["resources"][0]["fetcher"] = "Fetcher Fantasma"
    assert any("no está registrado" in e for e in validate_manifest(m, KNOWN))


def test_rechaza_inyeccion_class_path():
    m = _ok_manifest(); m["resources"][0]["class_path"] = "evil.Module.Pwn"
    errs = validate_manifest(m, KNOWN)
    assert any("class_path" in e and "prohibido" in e for e in errs)


def test_rechaza_inyeccion_ids():
    for campo in ("fetcher_id", "publisher_id", "id"):
        m = _ok_manifest(); m["resources"][0][campo] = "x"
        assert any(campo in e and "prohibido" in e for e in validate_manifest(m, KNOWN))


def test_params_mal_formados():
    m = _ok_manifest(); m["resources"][0]["params"] = [{"key": "url"}]  # falta value
    assert any("'key' y 'value'" in e for e in validate_manifest(m, KNOWN))


def test_resources_vacio():
    m = _ok_manifest(); m["resources"] = []
    assert any("no vacía" in e for e in validate_manifest(m, KNOWN))


def test_build_manifest_roundtrip_basico():
    pub = NS(acronimo="INE", nombre="INE", nivel="ESTATAL", pais="España", portal_url=None)
    res = NS(name="R1", schedule="0 0 * * *", active=True)
    fetcher = NS(code="API REST")
    params = [NS(key="url", value="https://x", is_external=False)]
    m = build_manifest(pub, [(res, fetcher, params)])
    assert m["odm_manifest_version"] == MANIFEST_VERSION
    assert m["publisher"]["acronimo"] == "INE"
    assert m["resources"][0]["fetcher"] == "API REST"
    assert m["resources"][0]["params"][0]["key"] == "url"
    # Un manifiesto exportado debe re-validar
    assert validate_manifest(m, {"API REST"}) == []


# --- plantilla (scaffold) -----------------------------------------------------

def test_template_manifest_excluye_params_bloqueados():
    from app.services.manifests import template_manifest, MANIFEST_VERSION
    t = template_manifest(
        "Web Tree", preset_code="Censo documental",
        preset_params={"extract_mode": "censo", "max_file_mb": 50},
        locked_params=["extract_mode"],
    )
    assert t["odm_manifest_version"] == MANIFEST_VERSION
    assert "_plantilla" in t
    r = t["resources"][0]
    assert r["fetcher"] == "Web Tree" and r["preset"] == "Censo documental"
    keys = {p["key"] for p in r["params"]}
    assert "extract_mode" not in keys          # lo fija el preset → fuera de params
    assert "max_file_mb" in keys               # editable
    assert "extract_mode" in t["_plantilla"]["params_fijados_por_preset"]


def test_template_manifest_se_vuelve_valido_al_rellenar():
    from app.services.manifests import template_manifest, validate_manifest
    t = template_manifest(
        "Web Tree", preset_code="Extracción de datos",
        preset_params={"extract_mode": "datos"}, locked_params=["extract_mode"],
    )
    # en crudo NO es válido (publisher.acronimo vacío); el _plantilla se ignora
    assert validate_manifest(t, {"Web Tree"})
    t["publisher"]["acronimo"] = "AYTOJEREZ"
    t["resources"][0]["name"] = "Jerez — económica (datos)"
    t["resources"][0]["params"].append(
        {"key": "root_url", "value": "https://transparencia.jerez.es/...", "is_external": False})
    assert validate_manifest(t, {"Web Tree"}) == []


def test_template_manifest_sin_preset_lista_disponibles():
    from app.services.manifests import template_manifest
    t = template_manifest("Web Tree", available_presets=["Censo documental", "Extracción de datos"])
    assert "preset" not in t["resources"][0]
    assert t["_plantilla"]["presets_disponibles"] == ["Censo documental", "Extracción de datos"]
