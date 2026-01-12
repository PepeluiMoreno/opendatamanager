"""
Script para poblar los parámetros de fetcher en la base de datos.
Ejecutar con: python -m scripts.seed_fetcher_params
"""
from uuid import uuid4
from app.database import SessionLocal
from app.models import Fetcher, FetcherParams


FETCHER_PARAMS = {
    "API REST": [
        {"param_name": "url", "required": True, "data_type": "string"},
        {"param_name": "method", "required": False, "data_type": "string"},
        {"param_name": "headers", "required": False, "data_type": "json"},
        {"param_name": "params", "required": False, "data_type": "json"},
        {"param_name": "body", "required": False, "data_type": "json"},
    ],
    "HTML Forms": [
        {"param_name": "url", "required": True, "data_type": "string"},
        {"param_name": "rows_selector", "required": True, "data_type": "string"},
        {"param_name": "headers", "required": False, "data_type": "json"},
        {"param_name": "total_text_selector", "required": False, "data_type": "json"},
        {"param_name": "next_page_selector", "required": False, "data_type": "string"},
        {"param_name": "page_param_name", "required": False, "data_type": "string"},
        {"param_name": "max_pages", "required": False, "data_type": "integer"},
        {"param_name": "delay_between_pages", "required": False, "data_type": "float"},
        {"param_name": "fields_mapping", "required": False, "data_type": "json"},
    ],
}


def seed_fetcher_params():
    """Puebla la tabla type_fetcher_params con los parámetros de cada fetcher"""
    db = SessionLocal()
    try:
        for fetcher_name, params_list in FETCHER_PARAMS.items():
            # Buscar el fetcher por nombre
            fetcher = db.query(Fetcher).filter(Fetcher.name == fetcher_name).first()

            if not fetcher:
                print(f"[WARN] Fetcher '{fetcher_name}' no encontrado, saltando...")
                continue

            print(f"\n[INFO] Procesando fetcher '{fetcher_name}' (ID: {fetcher.id})")

            # Eliminar parámetros existentes para este fetcher
            existing_params = db.query(FetcherParams).filter(
                FetcherParams.fetcher_id == fetcher.id
            ).all()

            if existing_params:
                print(f"  [INFO] Eliminando {len(existing_params)} parámetros existentes...")
                for param in existing_params:
                    db.delete(param)
                db.flush()

            # Crear nuevos parámetros
            for param_data in params_list:
                param = FetcherParams(
                    id=uuid4(),
                    fetcher_id=fetcher.id,
                    param_name=param_data["param_name"],
                    required=param_data["required"],
                    data_type=param_data["data_type"]
                )
                db.add(param)
                print(f"  [+] Añadido parámetro '{param_data['param_name']}' "
                      f"(required: {param_data['required']}, type: {param_data['data_type']})")

        db.commit()
        print("\n[OK] Parámetros de fetchers poblados correctamente")

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Error al poblar parámetros: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_fetcher_params()
