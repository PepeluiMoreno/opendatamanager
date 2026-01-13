from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text('ALTER TABLE opendata.fetcher ADD COLUMN IF NOT EXISTS class_path VARCHAR(255)'))
    conn.commit()
    print("Column class_path added successfully")
