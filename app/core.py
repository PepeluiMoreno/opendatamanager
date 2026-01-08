# app/core.py
"""
/app/core.py
Upsert genérico para cualquier tabla del esquema opendata
"""
from typing import Any, List
from sqlalchemy.orm import Session

def upsert(session: Session, target_model: str, data: Any, mode: str = "replace") -> None:
    """
    target_model: "geografia", "bdns", etc. (sin punto)
    data: lista de dicts o dict único
    mode: solo "replace" (DELETE + INSERT) por ahora
    """
    table = target_model.split(".")[0] if "." in target_model else target_model
    items = data if isinstance(data, list) else [data]

    if mode == "replace":
        session.execute(f"DELETE FROM opendata.{table}")
    for item in items:
        cols = ", ".join(item.keys())
        vals = ", ".join([f"%({k})s" for k in item.keys()])
        sql = f"INSERT INTO opendata.{table} ({cols}) VALUES ({vals})"
        session.execute(sql, item)
    session.commit()