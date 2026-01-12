"""
Script para repoblar resources de ejemplo.
Ejecutar con: python -m scripts.reseed_resources
"""
from uuid import uuid4
from app.database import SessionLocal
from app.models import FetcherType, Resource, ResourceParam


SAMPLE_RESOURCES = [
    {
        "name": "RER - Entidades Religiosas Católicas Madrid",
        "publisher": "Ministerio de Justicia",
        "target_table": "rer_entities",
        "fetcher_code": "HTML Forms",
        "active": True,
        "params": [
            {"key": "url", "value": "http://maper.mjusticia.gob.es/Maper/RER.action"},
            {"key": "method", "value": "GET"},
            {"key": "timeout", "value": "60"},
            {"key": "confesion", "value": "CATÓLICOS"},
            {"key": "comunidad", "value": "MADRID"},
            {"key": "seccion", "value": "TODAS"},
        ]
    },
    {
        "name": "RER - Entidades Evangélicas",
        "publisher": "Ministerio de Justicia",
        "target_table": "rer_entities",
        "fetcher_code": "HTML Forms",
        "active": True,
        "params": [
            {"key": "url", "value": "http://maper.mjusticia.gob.es/Maper/RER.action"},
            {"key": "method", "value": "GET"},
            {"key": "timeout", "value": "60"},
            {"key": "confesion", "value": "EVANGÉLICOS"},
            {"key": "seccion", "value": "GENERAL"},
        ]
    },
    {
        "name": "API REST Ejemplo - JSONPlaceholder",
        "publisher": "JSONPlaceholder",
        "target_table": "demo_posts",
        "fetcher_code": "API REST",
        "active": True,
        "params": [
            {"key": "url", "value": "https://jsonplaceholder.typicode.com/posts"},
            {"key": "method", "value": "GET"},
            {"key": "timeout", "value": "30"},
        ]
    },
]


def reseed_resources():
    """Elimina resources existentes y crea nuevos de ejemplo"""
    db = SessionLocal()
    try:
        # Eliminar resources existentes
        existing_resources = db.query(Resource).all()
        for resource in existing_resources:
            db.delete(resource)
        db.commit()
        print(f"[OK] Eliminados {len(existing_resources)} resources existentes")

        # Crear nuevos resources
        for resource_data in SAMPLE_RESOURCES:
            fetcher = db.query(FetcherType).filter(
                FetcherType.code == resource_data["fetcher_code"]
            ).first()

            if not fetcher:
                print(f"[WARN] No se encontró FetcherType '{resource_data["fetcher_code"]}'")
                continue

            resource = Resource(
                id=uuid4(),
                name=resource_data["name"],
                publisher=resource_data["publisher"],
                target_table=resource_data["target_table"],
                fetcher_id=fetcher.id,
                active=resource_data["active"]
            )
            db.add(resource)
            db.flush()

            for param_data in resource_data["params"]:
                param = ResourceParam(
                    id=uuid4(),
                    resource_id=resource.id,
                    key=param_data["key"],
                    value=param_data["value"]
                )
                db.add(param)

            print(f"[+] Creado Resource '{resource_data["name"]}' (tipo: {fetcher.code})")

        db.commit()
        print("
[OK] Resources repoblados correctamente")

    except Exception as e:
        db.rollback()
        print(f"
[ERROR] Error al repoblar resources: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    reseed_resources()
