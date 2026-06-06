"""Candado selectivo (§6c): la factory ignora overrides de parámetros bloqueados."""
from types import SimpleNamespace

from app.fetchers.factory import FetcherFactory


def _resource(preset_locked, resource_params):
    pdef = [SimpleNamespace(param_name="url", default_value=None),
            SimpleNamespace(param_name="field_map", default_value=None),
            SimpleNamespace(param_name="delay", default_value="0")]
    preset = SimpleNamespace(deleted_at=None,
                             params={"field_map": '{"a": "b"}', "delay": "2"},
                             locked_params=preset_locked)
    fetcher = SimpleNamespace(code="API REST", class_path="app.fetchers.rest.RESTFetcher",
                              params_def=pdef, preset_params=None)
    params = [SimpleNamespace(key=k, value=v) for k, v in resource_params.items()]
    return SimpleNamespace(active=True, name="r", fetcher=fetcher, preset=preset, params=params)


def test_override_de_bloqueado_se_ignora():
    r = _resource(["field_map"], {"url": "http://x", "field_map": '{"hack": "si"}', "delay": "9"})
    f = FetcherFactory.create_from_resource(r)
    assert f.params["field_map"] == '{"a": "b"}'   # candado: manda la variante
    assert f.params["delay"] == "9"                # sin candado: manda el recurso


def test_ejecucion_tampoco_pisa_bloqueados_pero_si_internos():
    r = _resource(["field_map"], {"url": "http://x"})
    f = FetcherFactory.create_from_resource(r, execution_params={"field_map": "no", "_preview_limit": "3"})
    assert f.params["field_map"] == '{"a": "b"}'
    assert f.params["_preview_limit"] == "3"       # los internos _ siempre pasan
