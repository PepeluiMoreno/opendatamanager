"""Estrategia form_submit del registro de construcción de la petición."""
from app.fetchers.request_building import build_request


def test_form_submit_ensambla_cuerpo():
    r = build_request("form_submit", {
        "form_hidden": {"__VIEWSTATE": "abc", "__EVENTTARGET": ""},
        "search_field_name": "provincia",
    }, pivot="11")
    assert r["method"] == "POST"
    assert r["data"] == {"__VIEWSTATE": "abc", "__EVENTTARGET": "", "provincia": "11"}
    assert r["json"] is None
