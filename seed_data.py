import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import Application, Resource, DatasetSubscription

def seed():
    session = SessionLocal()
    try:
        print("Iniciando seeding de OpenDataManager...")

        # 1. Crear una Aplicación de ejemplo (GrantsSurveyor)
        app_id = str(uuid.uuid4())
        grants_surveyor = Application(
            id=app_id,
            name="GrantsSurveyor",
            description="Plataforma de investigación de subvenciones y contratos",
            webhook_url="https://webhook.site/example-uuid", # Cambiar por URL real
            webhook_secret="super-secret-key",
            active=True
        )
        session.merge(grants_surveyor)
        print(f"  - Aplicación 'GrantsSurveyor' registrada (ID: {app_id})")

        # 2. Definir Recursos (Fuentes de Datos)
        resources = [
            # --- AGE: PLACSP (Atom Paging) ---
            {
                "name": "PLACSP - Licitaciones (Perfiles Contratante)",
                "description": "Licitaciones diarias publicadas en la Plataforma de Contratación del Sector Público",
                "publisher": "Ministerio de Hacienda",
                "fetcher_type": "ATOM_PAGING",
                "fetcher_params": {
                    "url": "https://contrataciondelestado.es/sindicacion/sindicacion_643/licitacionesPerfilesContratanteCompleto3.atom",
                    "max_pages": 10,
                    "timeout": 60
                },
                "schedule": "0 8 * * *", # Todos los días a las 08:00
                "target_table": "licitaciones_placsp",
                "enable_load": True,
                "load_mode": "upsert"
            },
            {
                "name": "PLACSP - Contratos Menores",
                "description": "Contratos menores publicados en la PLACSP",
                "publisher": "Ministerio de Hacienda",
                "fetcher_type": "ATOM_PAGING",
                "fetcher_params": {
                    "url": "https://contrataciondelestado.es/sindicacion/sindicacion_1044/contratosMenoresPerfilesContratante.atom",
                    "max_pages": 5
                },
                "schedule": "30 8 * * *",
                "target_table": "contratos_menores_placsp",
                "enable_load": True,
                "load_mode": "upsert"
            },
            # --- AGE: BDNS (REST) ---
            {
                "name": "BDNS - Convocatorias",
                "description": "Convocatorias de subvenciones de la Base de Datos Nacional de Subvenciones",
                "publisher": "Intervención General de la Administración del Estado (IGAE)",
                "fetcher_type": "REST",
                "fetcher_params": {
                    "url": "https://www.pap.hacienda.gob.es/bdnstrans/api/convocatorias",
                    "method": "GET",
                    "params": {"vpd": "GE", "year": 2026}
                },
                "schedule": "0 9 * * *",
                "target_table": "convocatorias_bdns",
                "enable_load": True,
                "load_mode": "upsert"
            },
            # --- CCAA: Madrid (REST/CKAN) ---
            {
                "name": "Madrid - Contratos Adjudicados",
                "description": "Contratos adjudicados por la Comunidad de Madrid (vía CKAN API)",
                "publisher": "Comunidad de Madrid",
                "fetcher_type": "REST",
                "fetcher_params": {
                    "url": "https://datos.comunidad.madrid/catalogo/api/3/action/datastore_search",
                    "params": {"resource_id": "8a6ac0d0-7561-46a3-8845-636b0cc9577c"}
                },
                "schedule": "0 10 * * 1", # Lunes a las 10:00
                "target_table": "contratos_madrid",
                "enable_load": True,
                "load_mode": "replace"
            },
            # --- CCAA: Cataluña (REST/Socrata) ---
            {
                "name": "Cataluña - Registro de Subvenciones",
                "description": "Registro público de subvenciones y ayudas de la Generalitat de Catalunya",
                "publisher": "Generalitat de Catalunya",
                "fetcher_type": "REST",
                "fetcher_params": {
                    "url": "https://dadesobertes.gencat.cat/resource/7862-6u8p.json",
                    "params": {"$limit": 1000}
                },
                "schedule": "0 11 * * *",
                "target_table": "subvenciones_catalunya",
                "enable_load": True,
                "load_mode": "upsert"
            }
        ]

        for res_data in resources:
            res_id = str(uuid.uuid4())
            resource = Resource(
                id=res_id,
                **res_data,
                active=True,
                created_at=datetime.utcnow()
            )
            session.merge(resource)
            print(f"  - Recurso '{res_data['name']}' registrado.")

            # 3. Crear suscripción automática para GrantsSurveyor
            sub = DatasetSubscription(
                id=str(uuid.uuid4()),
                application_id=app_id,
                resource_id=res_id,
                auto_upgrade="minor", # Notificar parches y cambios menores automáticamente
                active=True
            )
            session.merge(sub)

        session.commit()
        print("\nSeeding completado con éxito.")
    except Exception as e:
        session.rollback()
        print(f"\nError durante el seeding: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    seed()
