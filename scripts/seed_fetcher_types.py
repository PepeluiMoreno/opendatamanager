"""
Script para poblar los tipos de fetcher en la base de datos.
Ejecutar con: python -m scripts.seed_fetchers
"""
from uuid import uuid4
from app.database import SessionLocal
from app.models import FetcherType
from app.fetchers.registry import FetcherRegistry


fetcherS = [
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


def seed_fetchers():
    """Puebla la tabla fetcher con los tipos básicos"""
    db = SessionLocal()
    try:
        for type_data in fetcherS:
            # Verificar si ya existe
            existing = db.query(FetcherType).filter(
                FetcherType.code == type_data["code"]
            ).first()

            if existing:
                print(f"[OK] FetcherType '{type_data['code']}' ya existe (ID: {existing.id})")
                # Registrar class_path y actualizar descripción por si cambiaron
                try:
                    FetcherRegistry.register_fetcher(existing.code, type_data["class_path"], type_data["description"])
                except Exception:
                    pass
                existing.description = type_data["description"]
            else:
                # Crear nuevo (no almacenamos class_path en BD)
                fetcher = FetcherType(
                    id=uuid4(),
                    code=type_data["code"],
                    description=type_data["description"]
                )
                db.add(fetcher)
                db.flush()
                try:
                    FetcherRegistry.register_fetcher(type_data["code"], type_data["class_path"], type_data["description"])
                except Exception:
                    pass
                print(f"[+] Creado FetcherType '{type_data['code']}' (ID: {fetcher.id})")

        db.commit()
        print("\n[OK] Fetcher types poblados correctamente")

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Error al poblar fetcher types: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_fetchers()
