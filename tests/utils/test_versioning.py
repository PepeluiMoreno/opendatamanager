"""Tests de la política de versionado de datasets (app/utils/versioning.py)."""
from types import SimpleNamespace

import pytest

from app.utils.versioning import compute_schema_diff, compute_next_version


def _props(**fields):
    return {"properties": dict(fields)}


def test_data_only_is_patch():
    d = compute_schema_diff(_props(a={"type": "string"}), _props(a={"type": "string"}))
    assert not d["breaking_changes"] and not d["minor_changes"]


def test_added_field_is_minor():
    d = compute_schema_diff(_props(a={"type": "string"}),
                            _props(a={"type": "string"}, b={"type": "integer"}))
    assert d["minor_changes"] and not d["breaking_changes"]
    assert "b" in d["added_fields"]


def test_removed_field_is_major():
    d = compute_schema_diff(_props(a={"type": "string"}, b={"type": "integer"}),
                            _props(a={"type": "string"}))
    assert d["breaking_changes"]
    assert "b" in d["removed_fields"]


def test_nested_type_change_is_major():
    old = _props(obj={"type": "object", "properties": {"x": {"type": "string"}}})
    new = _props(obj={"type": "object", "properties": {"x": {"type": "integer"}}})
    d = compute_schema_diff(old, new)
    assert d["breaking_changes"] and "obj.x" in d["type_changes"]


def test_array_item_change_is_major():
    old = _props(arr={"type": "array", "items": {"type": "string"}})
    new = _props(arr={"type": "array", "items": {"type": "integer"}})
    d = compute_schema_diff(old, new)
    assert d["breaking_changes"] and "arr[]" in d["type_changes"]


def test_format_change_is_major():
    d = compute_schema_diff(_props(f={"type": "string", "format": "date"}),
                            _props(f={"type": "string", "format": "date-time"}))
    assert d["breaking_changes"] and "f" in d["format_changes"]


def test_enum_widened_minor_narrowed_major():
    widened = compute_schema_diff(_props(e={"type": "string", "enum": ["a"]}),
                                  _props(e={"type": "string", "enum": ["a", "b"]}))
    assert widened["minor_changes"] and "e" in widened["enum_widened"]
    narrowed = compute_schema_diff(_props(e={"type": "string", "enum": ["a", "b"]}),
                                   _props(e={"type": "string", "enum": ["a"]}))
    assert narrowed["breaking_changes"] and "e" in narrowed["enum_narrowed"]


def test_required_changes():
    old = {"properties": {"a": {"type": "string"}}, "required": ["a"]}
    new = {"properties": {"a": {"type": "string"}}, "required": []}
    d = compute_schema_diff(old, new)
    assert d["breaking_changes"] and "a" in d["required_removed"]


@pytest.mark.parametrize("prev,new_schema,expected", [
    (None, {}, (1, 0, 0)),
    (SimpleNamespace(schema_json=_props(a={"type": "string"}), major_version=1, minor_version=2, patch_version=3),
     _props(a={"type": "string"}), (1, 2, 4)),  # patch
    (SimpleNamespace(schema_json=_props(a={"type": "string"}), major_version=1, minor_version=2, patch_version=3),
     _props(a={"type": "string"}, b={"type": "integer"}), (1, 3, 0)),  # minor
    (SimpleNamespace(schema_json=_props(a={"type": "string"}), major_version=1, minor_version=2, patch_version=3),
     _props(), (2, 0, 0)),  # major (removed)
])
def test_compute_next_version(prev, new_schema, expected):
    assert compute_next_version(prev, new_schema) == expected


def test_pinned_version_matcher():
    from app.utils.versioning import version_satisfies_pin as m
    assert m("1.2.3", "1.2.3")
    assert not m("1.2.4", "1.2.3")
    assert m("1.2.9", "1.2.*")
    assert not m("1.3.0", "1.2.*")
    assert m("1.5.0", "1.*")
    assert not m("2.0.0", "1.*")
    assert m("9.9.9", "*")
    assert m("1.0.0", None)
