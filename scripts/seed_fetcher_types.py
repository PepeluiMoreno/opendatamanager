"""
Script para poblar los tipos de fetcher en la base de datos.
Ejecutar con: python -m scripts.seed_fetcher_types
"""
from uuid import uuid4
from app.database import SessionLocal
from app.models import FetcherType


FETCHER_TYPES = [
    {
        "code": "API REST",
        "class_path": "app.fetchers.rest.RestFetcher",
        "description": "API RESTful con soporte para JSON/XML"
    },
    {
        "code": "HTML Forms",
        "class_path": "app.fetchers.html.HtmlFetcher",
        "description": "Formularios web HTML (scraping de páginas y formularios)"
    },
    # Tipos futuros (descomentar cuando se implementen)
    # {
    #     "code": "SOAP",
    #     "class_path": "app.fetchers.soap.SoapFetcher",
    #     "description": "Servicio web SOAP/WSDL"
    # },
    # {
    #     "code": "GraphQL",
    #     "class_path": "app.fetchers.graphql.GraphQLFetcher",
    #     "description": "API GraphQL"
    # },
    # {
    #     "code": "CSV/Files",
    #     "class_path": "app.fetchers.files.FileFetcher",
    #     "description": "Archivos estáticos (CSV, Excel, JSON, XML)"
    # },
]


def seed_fetcher_types():
    """Puebla la tabla fetcher_type con los tipos básicos"""
    db = SessionLocal()
    try:
        for type_data in FETCHER_TYPES:
            # Verificar si ya existe
            existing = db.query(FetcherType).filter(
                FetcherType.code == type_data["code"]
            ).first()

            if existing:
                print(f"[OK] FetcherType '{type_data['code']}' ya existe (ID: {existing.id})")
                # Actualizar class_path y description por si cambiaron
                existing.class_path = type_data["class_path"]
                existing.description = type_data["description"]
            else:
                # Crear nuevo
                fetcher_type = FetcherType(
                    id=uuid4(),
                    code=type_data["code"],
                    class_path=type_data["class_path"],
                    description=type_data["description"]
                )
                db.add(fetcher_type)
                print(f"[+] Creado FetcherType '{type_data['code']}' (ID: {fetcher_type.id})")

        db.commit()
        print("\n[OK] Fetcher types poblados correctamente")

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Error al poblar fetcher types: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_fetcher_types()
