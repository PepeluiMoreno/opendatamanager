from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text('ALTER TABLE opendata.type_fetcher_params ADD COLUMN IF NOT EXISTS enum_values JSONB'))
    conn.commit()
    print("Column enum_values added successfully")
