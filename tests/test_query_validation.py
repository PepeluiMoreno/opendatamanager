"""Validación sintáctica del param 'query' según el tipo de request."""
from app.services.query_validation import validar_query


def test_tipos_sin_query_no_validan():
    assert validar_query("query", None) is None
    assert validar_query("json_body", "") is None


def test_graphql_valida_y_rechaza():
    assert validar_query("graphql", "{ recursos { id } }") is None
    assert "GraphQL" in validar_query("graphql", "{ recursos { id }")  # llave sin cerrar


def test_sparql_forma_y_llaves():
    assert validar_query("sparql", "PREFIX r: <http://x>\nSELECT ?s WHERE { ?s ?p ?o }") is None
    assert "forma" in validar_query("sparql", "DAME TODO")
    assert "desequilibradas" in validar_query("sparql", "SELECT ?s WHERE { ?s ?p ?o")


def test_query_vacia_con_tipo_que_la_exige():
    assert "requiere" in validar_query("graphql", "  ")
