"""
Script para insertar datos reales del caso de uso de gobierno español.

Casos de uso:
1. DIR3 - Directorio Común de Unidades Orgánicas
2. BDNS - Base de Datos Nacional de Subvenciones
3. INE - Instituto Nacional de Estadística
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from uuid import uuid4
from app.database import SessionLocal
from app.models import Fetcher, FetcherParams, Resource, ResourceParam, Application

def seed_real_data():
    """Seed database with real government open data use cases"""
    session = SessionLocal()

    try:
        print("Seeding real data for government open data use cases...")

        # Clean existing data (optional - comment out if you want to keep existing data)
        print("\nCleaning existing data...")
        session.query(ResourceParam).delete()
        session.query(Resource).delete()
        session.query(FetcherParams).delete()
        session.query(Fetcher).delete()
        session.query(Application).delete()
        session.commit()

        # ==================== FETCHERS ====================
        print("\nCreating Fetchers...")

        # 1. API REST Fetcher
        fetcher_rest = Fetcher(
            id=uuid4(),
            name="API REST",
            description="Fetcher for RESTful APIs with JSON responses"
        )
        session.add(fetcher_rest)
        session.flush()

        # REST Fetcher Parameters
        rest_params = [
            FetcherParams(id=uuid4(), fetcher_id=fetcher_rest.id, param_name="url", required=True, data_type="string"),
            FetcherParams(id=uuid4(), fetcher_id=fetcher_rest.id, param_name="method", required=False, data_type="string"),
            FetcherParams(id=uuid4(), fetcher_id=fetcher_rest.id, param_name="headers", required=False, data_type="json"),
            FetcherParams(id=uuid4(), fetcher_id=fetcher_rest.id, param_name="query_params", required=False, data_type="json"),
            FetcherParams(id=uuid4(), fetcher_id=fetcher_rest.id, param_name="timeout", required=False, data_type="integer"),
            FetcherParams(id=uuid4(), fetcher_id=fetcher_rest.id, param_name="max_retries", required=False, data_type="integer"),
        ]
        session.add_all(rest_params)
        print(f"   Created 'API REST' fetcher with {len(rest_params)} parameters")

        # 2. HTML Forms Fetcher (Paginated)
        fetcher_html = Fetcher(
            id=uuid4(),
            name="HTML Forms",
            description="Fetcher for HTML forms with pagination support"
        )
        session.add(fetcher_html)
        session.flush()

        # HTML Fetcher Parameters
        html_params = [
            FetcherParams(id=uuid4(), fetcher_id=fetcher_html.id, param_name="url", required=True, data_type="string"),
            FetcherParams(id=uuid4(), fetcher_id=fetcher_html.id, param_name="rows_selector", required=True, data_type="string"),
            FetcherParams(id=uuid4(), fetcher_id=fetcher_html.id, param_name="pagination_type", required=False, data_type="string"),
            FetcherParams(id=uuid4(), fetcher_id=fetcher_html.id, param_name="max_pages", required=False, data_type="integer"),
            FetcherParams(id=uuid4(), fetcher_id=fetcher_html.id, param_name="delay_between_requests", required=False, data_type="integer"),
            FetcherParams(id=uuid4(), fetcher_id=fetcher_html.id, param_name="has_header", required=False, data_type="boolean"),
            FetcherParams(id=uuid4(), fetcher_id=fetcher_html.id, param_name="clean_html", required=False, data_type="boolean"),
        ]
        session.add_all(html_params)
        print(f"   Created 'HTML Forms' fetcher with {len(html_params)} parameters")

        session.commit()

        # ==================== RESOURCES ====================
        print("\nCreating Resources...")

        # 1. DIR3 - Unidades Orgánicas
        resource_dir3_units = Resource(
            id=uuid4(),
            name="DIR3 - Unidades Orgánicas",
            description="Directorio Común de Unidades y Oficinas - Listado de unidades orgánicas de la AGE",
            publisher="Min. Hacienda y Función Pública",
            target_table="dir3_units",
            fetcher_id=fetcher_rest.id,
            active=True,
            enable_load=False,
            load_mode="replace"
        )
        session.add(resource_dir3_units)
        session.flush()

        dir3_params = [
            ResourceParam(id=uuid4(), resource_id=resource_dir3_units.id, key="url", value="https://api.dir3.es/unidades"),
            ResourceParam(id=uuid4(), resource_id=resource_dir3_units.id, key="method", value="GET"),
            ResourceParam(id=uuid4(), resource_id=resource_dir3_units.id, key="timeout", value="30"),
        ]
        session.add_all(dir3_params)
        print(f"   Created '{resource_dir3_units.name}' resource")

        # 2. DIR3 - Oficinas
        resource_dir3_offices = Resource(
            id=uuid4(),
            name="DIR3 - Oficinas",
            description="Directorio de oficinas de atención al ciudadano de la AGE",
            publisher="Min. Hacienda y Función Pública",
            target_table="dir3_offices",
            fetcher_id=fetcher_rest.id,
            active=True,
            enable_load=False,
            load_mode="replace"
        )
        session.add(resource_dir3_offices)
        session.flush()

        dir3_offices_params = [
            ResourceParam(id=uuid4(), resource_id=resource_dir3_offices.id, key="url", value="https://api.dir3.es/oficinas"),
            ResourceParam(id=uuid4(), resource_id=resource_dir3_offices.id, key="method", value="GET"),
            ResourceParam(id=uuid4(), resource_id=resource_dir3_offices.id, key="timeout", value="30"),
        ]
        session.add_all(dir3_offices_params)
        print(f"   Created '{resource_dir3_offices.name}' resource")

        # 3. BDNS - Subvenciones
        resource_bdns = Resource(
            id=uuid4(),
            name="BDNS - Convocatorias de Subvenciones",
            description="Base de Datos Nacional de Subvenciones - Convocatorias publicadas via API REST",
            publisher="IGAE",
            target_table="bdns_grants",
            fetcher_id=fetcher_rest.id,
            active=True,
            enable_load=False,
            load_mode="replace"
        )
        session.add(resource_bdns)
        session.flush()

        bdns_params = [
            ResourceParam(id=uuid4(), resource_id=resource_bdns.id, key="url", value="https://www.infosubvenciones.es/bdnstrans/api/convocatorias/busqueda"),
            ResourceParam(id=uuid4(), resource_id=resource_bdns.id, key="method", value="GET"),
            ResourceParam(id=uuid4(), resource_id=resource_bdns.id, key="query_params", value='{"page": "0", "pageSize": "100", "order": "numeroConvocatoria", "direccion": "desc", "vpd": "GE"}'),
            ResourceParam(id=uuid4(), resource_id=resource_bdns.id, key="timeout", value="60"),
        ]
        session.add_all(bdns_params)
        print(f"   Created '{resource_bdns.name}' resource")

        # 4. INE - Población por municipios
        resource_ine_pop = Resource(
            id=uuid4(),
            name="INE - Población por Municipios",
            description="Instituto Nacional de Estadística - Cifras oficiales de población municipal",
            publisher="Instituto Nacional de Estadística",
            target_table="ine_population",
            fetcher_id=fetcher_rest.id,
            active=True,
            enable_load=False,
            load_mode="replace"
        )
        session.add(resource_ine_pop)
        session.flush()

        ine_params = [
            ResourceParam(id=uuid4(), resource_id=resource_ine_pop.id, key="url", value="https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/2852"),
            ResourceParam(id=uuid4(), resource_id=resource_ine_pop.id, key="method", value="GET"),
            ResourceParam(id=uuid4(), resource_id=resource_ine_pop.id, key="timeout", value="60"),
            ResourceParam(id=uuid4(), resource_id=resource_ine_pop.id, key="max_retries", value="3"),
        ]
        session.add_all(ine_params)
        print(f"   Created '{resource_ine_pop.name}' resource")

        # 5. Datos.gob.es - Catálogo de datos
        resource_datosgob = Resource(
            id=uuid4(),
            name="Datos.gob.es - Catálogo",
            description="Catálogo de datos abiertos del sector público español",
            publisher="Min. Asuntos Económicos",
            target_table="datosgob_catalog",
            fetcher_id=fetcher_rest.id,
            active=False,  # Inactive by default
            enable_load=False,
            load_mode="replace"
        )
        session.add(resource_datosgob)
        session.flush()

        datosgob_params = [
            ResourceParam(id=uuid4(), resource_id=resource_datosgob.id, key="url", value="https://datos.gob.es/apidata/catalog/dataset"),
            ResourceParam(id=uuid4(), resource_id=resource_datosgob.id, key="method", value="GET"),
            ResourceParam(id=uuid4(), resource_id=resource_datosgob.id, key="timeout", value="45"),
        ]
        session.add_all(datosgob_params)
        print(f"   Created '{resource_datosgob.name}' resource (inactive)")

        session.commit()

        # ==================== APPLICATIONS ====================
        print("\nCreating Applications...")

        # 1. Portal de Transparencia
        app_transparency = Application(
            id=uuid4(),
            name="Portal de Transparencia",
            description="Portal público de transparencia del gobierno",
            models_path="/apps/transparency/models/",
            subscribed_resources=["dir3_units", "dir3_offices", "bdns_grants"],
            active=True,
            webhook_url="https://transparency.gob.es/webhook/odm",
            webhook_secret="secret_transparency_2024"
        )
        session.add(app_transparency)
        print(f"   Created '{app_transparency.name}' application")

        # 2. Sistema de Gestión de Subvenciones
        app_grants = Application(
            id=uuid4(),
            name="Sistema de Gestión de Subvenciones",
            description="Aplicación interna para gestión de subvenciones",
            models_path="/apps/grants/models/",
            subscribed_resources=["bdns_grants", "dir3_units"],
            active=True,
            webhook_url="https://grants-internal.gob.es/api/odm-webhook",
            webhook_secret="secret_grants_mgmt_2024"
        )
        session.add(app_grants)
        print(f"   Created '{app_grants.name}' application")

        # 3. Dashboard Analítico
        app_analytics = Application(
            id=uuid4(),
            name="Dashboard Analítico",
            description="Dashboard de análisis de datos públicos",
            models_path="/apps/analytics/models/",
            subscribed_resources=["ine_population", "bdns_grants"],
            active=True,
            webhook_url="https://analytics-dashboard.gob.es/webhooks/data-update",
            webhook_secret="secret_analytics_2024"
        )
        session.add(app_analytics)
        print(f"   Created '{app_analytics.name}' application")

        # 4. App Móvil Ciudadana (inactive)
        app_mobile = Application(
            id=uuid4(),
            name="App Móvil Ciudadana",
            description="Aplicación móvil para ciudadanos (en desarrollo)",
            models_path="/apps/mobile/models/",
            subscribed_resources=["dir3_offices"],
            active=False,
            webhook_url="https://mobile-api.gob.es/odm/notify",
            webhook_secret="secret_mobile_dev_2024"
        )
        session.add(app_mobile)
        print(f"   Created '{app_mobile.name}' application (inactive)")

        session.commit()

        # ==================== SUMMARY ====================
        print("\n" + "="*60)
        print("SEED COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"\nSummary:")
        print(f"   - Fetchers created: 2")
        print(f"   - Fetcher parameters: {len(rest_params) + len(html_params)}")
        print(f"   - Resources created: 5 (4 active, 1 inactive)")
        print(f"   - Resource parameters: {len(dir3_params) + len(dir3_offices_params) + len(bdns_params) + len(ine_params) + len(datosgob_params)}")
        print(f"   - Applications created: 4 (3 active, 1 inactive)")
        print("\nUse cases:")
        print("   1. DIR3 - Government organizational structure")
        print("   2. BDNS - National grants database")
        print("   3. INE - National statistics")
        print("   4. Datos.gob.es - Open data catalog")
        print("\nReady to test in the UI!")
        print("   - Dashboard: http://localhost:5173/")
        print("   - Fetchers: http://localhost:5173/fetchers")
        print("   - Resources: http://localhost:5173/resources")
        print("   - Applications: http://localhost:5173/applications")

    except Exception as e:
        print(f"\nError seeding data: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_real_data()
