"""Tests del guardia de integridad (sin BD): la lógica pura `contract_changes` y
las decisiones de bloqueo, con los conteos monkeypatcheados."""
from types import SimpleNamespace as NS

import pytest

import app.services.integrity as integ
from app.services.integrity import (
    contract_changes, guard_preset_update, guard_resource_delete, guard_resource_update,
)


def _p(k, v):
    return NS(key=k, value=v)


def test_contract_changes_detecta_fetcher_preset_params():
    res = NS(id="r", fetcher_id="f1", preset_id="p1")
    assert contract_changes(res, NS(fetcher_id="f2", preset_id=None, params=None), {}) == {"fetcher"}
    assert contract_changes(res, NS(fetcher_id=None, preset_id="p2", params=None), {}) == {"preset"}
    assert contract_changes(res, NS(fetcher_id=None, preset_id="", params=None), {}) == {"preset"}  # limpiar preset
    assert contract_changes(res, NS(fetcher_id=None, preset_id=None, params=[_p("root_url", "u2")]),
                            {"root_url": "u1"}) == {"params"}


def test_contract_changes_ignora_no_op_y_campos_seguros():
    res = NS(id="r", fetcher_id="f1", preset_id="p1")
    assert contract_changes(res, NS(fetcher_id="f1", preset_id="p1", params=[_p("root_url", "u")]),
                            {"root_url": "u"}) == set()                      # mismos valores
    assert contract_changes(res, NS(fetcher_id=None, preset_id=None, params=None),
                            {"root_url": "u"}) == set()                      # no toca contrato


def test_guard_update_bloquea_solo_con_suscripciones(monkeypatch):
    res = NS(id="r", name="X", fetcher_id="f1", preset_id="p1")
    cambia = NS(fetcher_id="f2", preset_id=None, params=None)
    monkeypatch.setattr(integ, "_current_params", lambda s, rid: {})

    monkeypatch.setattr(integ, "active_subscription_count", lambda s, rid: 3)
    with pytest.raises(ValueError):
        guard_resource_update(None, res, cambia)

    monkeypatch.setattr(integ, "active_subscription_count", lambda s, rid: 0)
    guard_resource_update(None, res, cambia)                                 # sin subs → pasa

    monkeypatch.setattr(integ, "active_subscription_count", lambda s, rid: 3)
    guard_resource_update(None, res, NS(fetcher_id="f1", preset_id=None, params=None))  # no-contrato → pasa


def test_guard_delete_bloquea_con_suscripciones(monkeypatch):
    res = NS(id="r", name="X")
    monkeypatch.setattr(integ, "active_subscription_count", lambda s, rid: 1)
    with pytest.raises(ValueError):
        guard_resource_delete(None, res)
    monkeypatch.setattr(integ, "active_subscription_count", lambda s, rid: 0)
    guard_resource_delete(None, res)


def test_guard_preset_update(monkeypatch):
    preset = NS(id="p", code="Extracción de datos")
    monkeypatch.setattr(integ, "preset_active_subscription_count", lambda s, pid: 2)
    with pytest.raises(ValueError):
        guard_preset_update(None, preset, changing_contract=True)
    guard_preset_update(None, preset, changing_contract=False)               # sin cambio de contrato → pasa
    monkeypatch.setattr(integ, "preset_active_subscription_count", lambda s, pid: 0)
    guard_preset_update(None, preset, changing_contract=True)                # cambio sin subs → pasa
