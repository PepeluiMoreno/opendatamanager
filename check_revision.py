from sqlalchemy import create_engine, text

engine = create_engine('postgresql://postgres:root@localhost:5433/opendatamanager')
with engine.connect() as conn:
    result = conn.execute(text('SELECT version_num FROM alembic_version'))
    row = result.fetchone()
    if row:
        print(f"Current database revision: {row[0]}")
    else:
        print("No revision in database")
