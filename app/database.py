import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

# 1.  Schema por defecto
SCHEMA = os.getenv("DATABASE_SCHEMA", "opendata")

DATABASE_URL = (
    f"postgresql+psycopg2://{os.getenv('DATABASE_USER')}:{os.getenv('DATABASE_PASSWORD')}"
    f"@{os.getenv('DATABASE_HOST')}:{os.getenv('DATABASE_PORT')}/{os.getenv('DATABASE_DBNAME')}"
    f"?sslmode={os.getenv('DATABASE_SSL_MODE', 'require')}"
)

# 2.  Engine con search_path fijo
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"options": f"-csearch_path={SCHEMA}"}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3.  Base cuyo metadata ya lleva el schema
Base = declarative_base(metadata=declarative_base().metadata)
Base.metadata.schema = SCHEMA