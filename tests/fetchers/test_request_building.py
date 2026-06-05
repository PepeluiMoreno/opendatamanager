"""Registro de construcción de la petición (categoría de variación, puro)."""
from app.fetchers.request_building import build_request


def test_query_por_defecto_get_sin_cuerpo():
    r = build_request("query", {})
    assert r["method"] == "GET" and r["json"] is None and r["data"] is None


def test_json_body_con_plantilla_y_pivote():
    r = build_request("json_body", {"payload_template": {"codigoProvincia": "{pivot}", "nombre": ""}}, pivot="01")
    assert r["method"] == "POST"
    assert r["json"] == {"codigoProvincia": "01", "nombre": ""}


def test_graphql():
    r = build_request("graphql", {"graphql_query": "{ a }"})
    assert r["method"] == "POST"
    assert r["json"]["query"] == "{ a }"
    assert r["headers"]["Content-Type"] == "application/json"


def test_sparql():
    r = build_request("sparql", {"sparql_query": "SELECT * WHERE {?s ?p ?o}"})
    assert r["data"]["query"].startswith("SELECT")
    assert "sparql-results+json" in r["headers"]["Accept"]


def test_graphql_y_sparql_leen_query_unificada():
    r = build_request("graphql", {"query": "{ b }"})
    assert r["json"]["query"] == "{ b }"
    r = build_request("sparql", {"query": "ASK { ?s ?p ?o }"})
    assert r["data"]["query"].startswith("ASK")
