import os, textwrap, pprint
from dotenv import load_dotenv
load_dotenv()          # <-- carga el .env que está en la carpeta RAÍZ del proyecto

print('\n=== ENV que ve SQLAlchemy ===')
pprint.pprint({k: os.getenv(k) for k in (
    'DATABASE_USER','DATABASE_PASSWORD','DATABASE_HOST',
    'DATABASE_PORT','DATABASE_DBNAME','DATABASE_SSL_MODE')})

print('\n=== URL que construye env.py ===')
url = (f'postgresql+psycopg2://{os.getenv("DATABASE_USER")}:'
       f'{os.getenv("DATABASE_PASSWORD")}@'
       f'{os.getenv("DATABASE_HOST")}:{os.getenv("DATABASE_PORT")}/'
       f'{os.getenv("DATABASE_DBNAME")}?sslmode='
       f'{os.getenv("DATABASE_SSL_MODE","require")}')
print(textwrap.fill(url, width=80))