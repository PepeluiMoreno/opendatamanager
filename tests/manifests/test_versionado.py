"""Tests del canónico/hash del versionado de manifiestos (funciones puras)."""
from app.services.manifests import canonical_resource, manifest_hash


def test_canonico_determinista_e_independiente_del_orden_de_params():
    a = canonical_resource("R", "API REST", "0 5 * * *", True,
                           [{"key": "b", "value": "2"}, {"key": "a", "value": "1"}])
    b = canonical_resource("R", "API REST", "0 5 * * *", True,
                           [{"key": "a", "value": "1"}, {"key": "b", "value": "2"}])
    assert a == b
    assert manifest_hash(a) == manifest_hash(b)


def test_hash_cambia_si_cambia_un_valor():
    base = canonical_resource("R", "API REST", None, True, [{"key": "url", "value": "x"}])
    mod = canonical_resource("R", "API REST", None, True, [{"key": "url", "value": "y"}])
    assert manifest_hash(base) != manifest_hash(mod)


def test_hash_cambia_si_cambia_schedule_o_active():
    a = canonical_resource("R", "F", "0 5 * * *", True, [])
    assert manifest_hash(a) != manifest_hash(canonical_resource("R", "F", "0 6 * * *", True, []))
    assert manifest_hash(a) != manifest_hash(canonical_resource("R", "F", "0 5 * * *", False, []))


def test_is_external_se_incluye_en_el_canonico():
    a = canonical_resource("R", "F", None, True, [{"key": "k", "value": "v", "is_external": True}])
    b = canonical_resource("R", "F", None, True, [{"key": "k", "value": "v", "is_external": False}])
    assert manifest_hash(a) != manifest_hash(b)
