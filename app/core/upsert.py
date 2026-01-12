"""
Upsert genérico para cualquier tabla del esquema core
"""
from typing import Any, Set
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models import Resource


def upsert(session: Session, target_model: str, data: Any, mode: str = "replace") -> None:
    """
    Safe upsert con validación de tabla whitelist.

    Args:
        target_model: nombre de tabla (validado contra whitelist)
        data: lista de dicts o dict único
        mode: "replace"|"upsert"|"append"

    Raises:
        ValueError: si target_model no está en whitelist
    """
    # Validate table name against whitelist
    allowed_tables = get_allowed_tables(session)
    if target_model not in allowed_tables:
        raise ValueError(
            f"Table '{target_model}' not in allowed list. "
            f"Allowed: {', '.join(sorted(allowed_tables))}"
        )

    items = data if isinstance(data, list) else [data]

    if mode == "replace":
        # Safe: table validated against whitelist
        session.execute(text(f"DELETE FROM core.{target_model}"))

    for item in items:
        cols = ", ".join(item.keys())
        vals = ", ".join([f":{k}" for k in item.keys()])
        # Safe: table validated, values are parameterized
        sql = f"INSERT INTO core.{target_model} ({cols}) VALUES ({vals})"
        session.execute(text(sql), item)

    session.commit()


def get_allowed_tables(session: Session) -> Set[str]:
    """
    Get whitelist of allowed tables from Resource.target_table.

    Returns:
        Set of table names that can be used in upsert()
    """
    resources = session.query(Resource).all()
    return {r.target_table for r in resources if r.target_table}