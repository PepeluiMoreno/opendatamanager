from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_schema='opendata' AND table_name='type_fetcher_params' ORDER BY ordinal_position"))
    print("Columns in type_fetcher_params:")
    for row in result:
        print(f"  {row[0]}: {row[1]}")
