"""
Compat wrapper del seed base de fetchers.

El alta inicial de fetchers se hace a través de la API de administración
GraphQL en `seed_fetchers.py`, que es el único seed automático previsto para
despliegue.
"""

from seed_fetchers import seed


if __name__ == "__main__":
    seed()
