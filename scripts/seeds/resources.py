"""
Seed 03 — Concrete resources.

Inserts/updates all known resources and their params.
Safe to run multiple times (upsert by name).

Run standalone:
    python -m scripts.seeds.resources
"""
from sqlalchemy import text
from scripts.seeds._db import get_session

# Each resource references its fetcher by name (DB column 'name').
# params: dict of key→value for resource_param rows.
# is_external=True means the param is prompted at execution time.
RESOURCES = [
    # ------------------------------------------------------------------ BDNS
    {
        "name": "BDNS - Convocatorias de Subvenciones",
        "publisher": "IGAE",
        "target_table": "bdns_grants",
        "active": True,
        "fetcher": "API REST Paginada",
        "schedule": "0 3 * * 1",  # Every Monday at 03:00
        "params": {
            "url":             "https://www.infosubvenciones.es/bdnstrans/api/convocatorias/busqueda",
            "method":          "get",
            "page_param":      "page",
            "page_size_param": "pageSize",
            "page_size":       "10000",
            "content_field":   "content",
            "id_field":        "id",
            "timeout":         "60",
            "query_params":    '{"page": "0", "pageSize": "100", "order": "numeroConvocatoria", "direccion": "desc", "vpd": "GE"}',
            "year":            "2026",
        },
        "external_params": {"year": True},
    },
    {
        "name": "BDNS - Concesiones de Subvenciones",
        "publisher": "IGAE",
        "target_table": "bdns_concesiones",
        "active": True,
        "fetcher": "API REST Paginada",
        "schedule": "0 4 * * 1",  # Every Monday at 04:00
        "params": {
            "url":             "https://www.infosubvenciones.es/bdnstrans/api/concesiones/busqueda",
            "page_param":      "page",
            "page_size_param": "pageSize",
            "page_size":       "10000",
            "content_field":   "content",
            "id_field":        "id",
            "year":            "2026",
        },
        "external_params": {"year": True},
    },

    # ------------------------------------------------------------------- INE
    {
        "name": "INE - Población por Municipios",
        "publisher": "Instituto Nacional de Estadística",
        "target_table": "ine_population",
        "active": True,
        "fetcher": "API REST",
        "schedule": "0 2 1 1 *",  # Every Jan 1st at 02:00
        "params": {
            "url":         "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/2852",
            "method":      "get",
            "timeout":     "60",
            "max_retries": "3",
        },
    },
    {
        "name": "Catalogos del INE",
        "publisher": "INE",
        "target_table": "",
        "active": True,
        "fetcher": "API REST",
        "schedule": None,
        "params": {
            "url": "https://datos.gob.es/apidata/catalog/dataset.json",
        },
    },

    # ----------------------------------------------- Junta de Andalucía
    {
        "name": "Bienes Inmuebles - Junta de Andalucía",
        "publisher": "Junta de Andalucía",
        "target_table": "",
        "active": True,
        "fetcher": "Feeds ATOM/RSS",
        "schedule": None,
        "params": {
            "base_url":      "https://www.juntadeandalucia.es/ssdigitales/datasets/contentapi/1.0.0/search/",
            "dataset_id":    "jda_buscador_bienes_inmuebles.atom",
            "format":        "atom",
            "page_size":     "50",
            "start_index":   "0",
            "max_pages":     "1",
            "sort":          "date:desc",
            "source_filter": "data",
            "verify_ssl":    "true",
            "timeout":       "30",
        },
    },

    # ----------------------------------------------- Ministerio de Justicia / RER
    {
        "name": "RER - Entidades Religiosas",
        "publisher": "Ministerio de Justicia",
        "target_table": "rer_entidades",
        "active": True,
        "fetcher": "HTML SearchLoop",
        "schedule": "0 3 * * 0",  # Every Sunday at 03:00
        "params": {
            "url":               "http://maper.mjusticia.gob.es/Maper/RER.action",
            "search_field_name": "comunidadAutonoma",
            "rows_selector":     "table.resultado tr",
            "method":            "POST",
            "delay_between_searches": "2",
            "timeout":           "60",
        },
    },
    {
        "name": "Fundaciones - Registro de Fundaciones",
        "publisher": "Ministerio de Justicia",
        "target_table": "fundaciones",
        "active": False,  # Pendiente de confirmar URL y params
        "fetcher": "HTML Paginated",
        "schedule": None,
        "params": {
            "url":            "https://www.mjusticia.gob.es/es/RegistroMercantil/RegistroFundaciones/",
            "rows_selector":  "table tr",
            "timeout":        "60",
        },
    },
    {
        "name": "Contrataciones del Estado - Licitaciones por Provincia",
        "publisher": "Ministerio de Hacienda",
        "target_table": "contrataciones_estado",
        "active": False,  # Pendiente de confirmar URL y search_field_name
        "fetcher": "HTML SearchLoop",
        "schedule": None,
        "params": {
            "url":               "https://contrataciondelestado.es/wps/portal/plataforma",
            "search_field_name": "provincia",
            "rows_selector":     "table tr",
            "delay_between_searches": "2",
            "timeout":           "60",
        },
    },

    # ----------------------------------------------- datos.gob.es
    {
        "name": "Datos.gob.es - Catálogo",
        "publisher": "Ministerio de Hacienda",
        "target_table": "datosgob_catalog",
        "active": True,
        "fetcher": "HTML Forms",
        "schedule": None,
        "params": {
            "url":     "https://datos.gob.es/apidata/catalog/dataset",
            "method":  "GET",
            "timeout": "45",
        },
    },
]


def seed(db=None):
    own_session = db is None
    if own_session:
        db = get_session()

    upserted = 0
    try:
        for r in RESOURCES:
            fetcher_row = db.execute(
                text("SELECT id FROM opendata.fetcher WHERE name = :name"),
                {"name": r["fetcher"]},
            ).fetchone()
            if not fetcher_row:
                print(f"  [resources] WARNING: fetcher '{r['fetcher']}' not found — skipping '{r['name']}'.")
                continue

            fetcher_id = fetcher_row[0]

            res_row = db.execute(
                text("""
                    INSERT INTO opendata.resource
                        (id, name, publisher, target_table, active, fetcher_id, schedule)
                    VALUES (
                        gen_random_uuid(), :name, :publisher, :target_table,
                        :active, :fetcher_id, :schedule
                    )
                    ON CONFLICT (name) DO UPDATE
                        SET publisher    = EXCLUDED.publisher,
                            target_table = EXCLUDED.target_table,
                            active       = EXCLUDED.active,
                            fetcher_id   = EXCLUDED.fetcher_id,
                            schedule     = EXCLUDED.schedule
                    RETURNING id
                """),
                {
                    "name":         r["name"],
                    "publisher":    r.get("publisher", ""),
                    "target_table": r.get("target_table", ""),
                    "active":       r.get("active", True),
                    "fetcher_id":   fetcher_id,
                    "schedule":     r.get("schedule"),
                },
            ).fetchone()
            resource_id = res_row[0]

            # Re-insert params: delete old ones and re-add (simpler than per-key upsert)
            db.execute(
                text("DELETE FROM opendata.resource_param WHERE resource_id = :rid"),
                {"rid": resource_id},
            )
            for key, value in r.get("params", {}).items():
                is_external = r.get("external_params", {}).get(key, False)
                db.execute(
                    text("""
                        INSERT INTO opendata.resource_param
                            (id, resource_id, key, value, is_external)
                        VALUES (gen_random_uuid(), :resource_id, :key, :value, :is_external)
                    """),
                    {
                        "resource_id": resource_id,
                        "key":         key,
                        "value":       str(value),
                        "is_external": is_external,
                    },
                )
            upserted += 1

        db.commit()
        print(f"  [resources] {upserted} resources upserted.")
    except Exception:
        db.rollback()
        raise
    finally:
        if own_session:
            db.close()


if __name__ == "__main__":
    seed()
