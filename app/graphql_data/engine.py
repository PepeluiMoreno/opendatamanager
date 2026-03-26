"""
engine.py — Singleton que mantiene el GraphQLSchema vivo para /graphql/data.

El schema se construye la primera vez que se llama a `rebuild()` y se reemplaza
atómicamente cada vez que se vuelve a llamar (por ejemplo, al completar una
ejecución).  La operación es thread-safe porque la asignación de una referencia
en Python es atómica (GIL).

Uso típico:
    from app.graphql_data import engine

    # Al arrancar la app — construye el schema con los datasets actuales en BD
    await engine.rebuild(db)

    # Al completar una ejecución — actualiza el schema con los nuevos datos
    engine.rebuild(db)

    # Para ejecutar una query GraphQL
    result = engine.execute(query_string, variables)
"""

import threading
from typing import Optional

from graphql import GraphQLSchema, graphql_sync

from app.graphql_data.schema_builder import build_schema


# ── Estado global (module-level singleton) ────────────────────────────────────

_schema: Optional[GraphQLSchema] = None
_registry: list[dict] = []
_lock = threading.Lock()           # Para rebuild() concurrente (poco probable pero seguro)
_schema_version: int = 0           # Incrementa en cada rebuild; útil para debug


# ── API pública ───────────────────────────────────────────────────────────────

def rebuild(db) -> int:
    """
    Reconstruye el schema leyendo los datasets actuales de la BD.

    Llama a `schema_builder.build_schema(db)`, que:
      - Consulta el Dataset más reciente por resource con data_path válido.
      - Lee los primeros 200 registros de cada JSONL para inferir campos.
      - Genera un GraphQLObjectType + resolver por dataset.

    Returns:
        Número de datasets expuestos en el nuevo schema.

    Thread-safety:
        El lock garantiza que dos rebuilds simultáneos no se pisen.
        Una vez terminado, el schema se publica como referencia atómica.
    """
    global _schema, _registry, _schema_version

    new_schema, new_registry = build_schema(db)

    with _lock:
        _schema = new_schema
        _registry = new_registry
        _schema_version += 1
        version = _schema_version

    count = len(new_registry)
    print(f"[graphql_data] Schema v{version} built — {count} dataset(s) exposed.")
    return count


def get_schema() -> Optional[GraphQLSchema]:
    """Devuelve el schema actual (None si aún no se ha llamado rebuild)."""
    return _schema


def get_registry() -> list[dict]:
    """Devuelve la lista de metadatos de los datasets expuestos."""
    return list(_registry)


def get_version() -> int:
    """Número de veces que se ha llamado rebuild (útil para pruebas/debug)."""
    return _schema_version


def execute(query: str, variables: Optional[dict] = None, context: Optional[dict] = None):
    """
    Ejecuta una query GraphQL sobre el schema actual de forma síncrona.

    Args:
        query     — Cadena GraphQL (query o fragment).
        variables — Variables de la query (dict o None).
        context   — Contexto pasado a los resolvers (raramente necesario aquí).

    Returns:
        graphql.ExecutionResult con campos `.data` y `.errors`.

    Raises:
        RuntimeError si el schema aún no ha sido construido (rebuild no llamado).
    """
    schema = _schema
    if schema is None:
        raise RuntimeError(
            "El schema GraphQL de datos no está disponible. "
            "Llama a engine.rebuild(db) al arrancar la aplicación."
        )
    return graphql_sync(schema, query, variable_values=variables or {}, context_value=context)
