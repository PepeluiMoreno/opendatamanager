"""
Script para refrescar modelos de aplicaciones suscritas.
Lee las aplicaciones activas de la BD y regenera sus core.models.

Uso:
    python scripts/refresh_app_models.py
    python scripts/refresh_app_models.py --app-id <uuid>  # Solo una app
"""
import argparse
import os
from app.database import SessionLocal
from app.models import Application
from app.refresh.model_generator import ModelGenerator


def refresh_application(app: Application, api_url: str) -> None:
    """
    Refresca los modelos de una aplicación específica.

    Args:
        app: Instancia de Application
        api_url: URL de la API GraphQL
    """
    print(f"\n{'='*60}")
    print(f"Aplicación: {app.name}")
    print(f"Projects suscritos: {', '.join(app.subscribed_projects)}")
    print(f"Destino: {app.models_path}")
    print(f"{'='*60}\n")

    generator = ModelGenerator(api_url=api_url)
    generator.generate_models_for_application(
        app_name=app.name,
        subscribed_projects=app.subscribed_projects,
        models_path=app.models_path
    )


def main():
    parser = argparse.ArgumentParser(
        description="Refresca modelos de aplicaciones suscritas"
    )
    parser.add_argument(
        "--app-id",
        type=str,
        help="ID de la aplicación a refrescar (opcional, por defecto todas)"
    )
    args = parser.parse_args()

    if SessionLocal is None:
        print("❌ Error: DATABASE_URL no configurado en .env")
        return

    api_url = os.getenv("API_URL", "http://localhost:8040/graphql")

    with SessionLocal() as session:
        if args.app_id:
            # Refrescar solo una aplicación
            app = session.query(Application).filter(
                Application.id == args.app_id
            ).first()

            if not app:
                print(f"❌ Aplicación con id '{args.app_id}' no encontrada")
                return

            if not app.active:
                print(f"⚠️  Aplicación '{app.name}' está desactivada")
                return

            refresh_application(app, api_url)
        else:
            # Refrescar todas las aplicaciones activas
            apps = session.query(Application).filter(
                Application.active == True
            ).all()

            if not apps:
                print("⚠️  No hay aplicaciones activas para refrescar")
                return

            print(f"\n🔄 Refrescando {len(apps)} aplicaciones...\n")

            for app in apps:
                try:
                    refresh_application(app, api_url)
                except Exception as e:
                    print(f"❌ Error en aplicación '{app.name}': {e}")
                    continue

            print(f"\n✅ Refresh completado para todas las aplicaciones")


if __name__ == "__main__":
    main()
