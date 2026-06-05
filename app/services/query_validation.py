"""Validación sintáctica de consultas según su tipo (param 'request' del recurso).

Un solo param 'query' cuyo lenguaje lo decide la estrategia de construcción de la
petición: graphql se valida con graphql-core (parser real, ya presente vía
strawberry); sparql con una comprobación estructural ligera (forma de la consulta
y llaves equilibradas), suficiente para cazar errores de pegado sin arrastrar una
dependencia de parser SPARQL completo.
"""
import re
from typing import Optional

_TIPOS_CON_QUERY = {"graphql", "sparql"}
_SPARQL_FORMA = re.compile(
    r"^\s*(PREFIX\s+[^\n]+\n\s*)*(BASE\s+<[^>]*>\s*)?(SELECT|CONSTRUCT|ASK|DESCRIBE)\b",
    re.IGNORECASE,
)


def validar_query(tipo: Optional[str], texto: Optional[str]) -> Optional[str]:
    """Devuelve un mensaje de error si la query no es válida para su tipo; None si OK.
    Tipos sin lenguaje de consulta (query, json_body, form...) no se validan."""
    tipo = (tipo or "").lower()
    if tipo not in _TIPOS_CON_QUERY:
        return None
    if not texto or not texto.strip():
        return f"request={tipo} requiere el parámetro 'query' con la consulta."
    if tipo == "graphql":
        try:
            from graphql import parse
            parse(texto)
        except Exception as e:
            return f"La query GraphQL no es válida: {e}"
        return None
    # sparql: forma + llaves equilibradas
    if not _SPARQL_FORMA.search(texto):
        return ("La query SPARQL no tiene forma válida: debe empezar por "
                "SELECT/CONSTRUCT/ASK/DESCRIBE (con PREFIX opcionales).")
    if texto.count("{") != texto.count("}"):
        return "La query SPARQL tiene llaves '{}' desequilibradas."
    return None
