"""Seed PdfTableFetcher + recursos transparencia.jerez.es

Crea el registro del fetcher PDF_TABLE y los cuatro recursos de transparencia
del Ayuntamiento de Jerez de la Frontera (PMP mensual, morosidad trimestral,
deuda financiera anual, CESEL coste de servicios).

También registra CityDashboard como aplicación suscriptora si no existe,
y crea las suscripciones para los cuatro recursos.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b9
Create Date: 2026-04-19 10:00:00.000000
"""
from typing import Union, Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# UUIDs fijos para poder referenciarlos en downgrade y en CityDashboard
_FETCHER_ID     = "d4000001-0000-0000-0000-000000000001"
_RES_PMP_ID     = "d4000002-0000-0000-0000-000000000001"
_RES_MOR_ID     = "d4000003-0000-0000-0000-000000000001"
_RES_DEUDA_ID   = "d4000004-0000-0000-0000-000000000001"
_RES_CESEL_ID   = "d4000005-0000-0000-0000-000000000001"
_APP_ID         = "d4000006-0000-0000-0000-000000000001"

# URL base del portal de transparencia de Jerez
_BASE = "https://transparencia.jerez.es/infopublica/economica"

# Parámetros por recurso: (resource_id, name, description, target_table, params_list)
_RESOURCES = [
    (
        _RES_PMP_ID,
        "jerez_pmp_mensual",
        "PMP mensual — Ayuntamiento de Jerez y entidades dependientes (Ley 15/2010)",
        "jerez_pmp_mensual",
        [
            ("url_template", f"{_BASE}/c-deuda/{{year}}/pmp/Informe_PMP_{{year}}_{{month}}.pdf"),
            ("granularity",  "monthly"),
            ("year_from",    "2020"),
            ("year_to",      "2025"),
            ("table_index",  "0"),
            ("header_row",   "0"),
        ],
    ),
    (
        _RES_MOR_ID,
        "jerez_morosidad_trimestral",
        "Morosidad trimestral Ley 15/2010 — Ayuntamiento de Jerez",
        "jerez_morosidad_trimestral",
        [
            # Patrón real: Informe_Ta_Ley_15_10-{year}-{quarter}oT... — el quarter placeholder
            # necesita mapeo 1→1oT, 2→2oT, etc.; se hace en el parser webhook de CityDashboard.
            # Aquí usamos {quarter} para que PdfTableFetcher construya T1…T4 en _quarter.
            ("url_template", f"{_BASE}/c-deuda/{{year}}/morosidad/Informe_Ta_Ley_15_10-{{year}}-{{quarter}}oT.pdf"),
            ("granularity",  "quarterly"),
            ("year_from",    "2020"),
            ("year_to",      "2025"),
            ("table_index",  "0"),
            ("header_row",   "0"),
        ],
    ),
    (
        _RES_DEUDA_ID,
        "jerez_deuda_financiera",
        "Deuda financiera a 31-dic — Ayuntamiento de Jerez",
        "jerez_deuda_financiera",
        [
            ("url_template", f"{_BASE}/c-deuda/{{year}}/deuda/DEUDA_FINANCIERA_31-12-{{year}}.pdf"),
            ("granularity",  "annual"),
            ("year_from",    "2020"),
            ("year_to",      "2024"),
            ("table_index",  "0"),
            ("header_row",   "0"),
        ],
    ),
    (
        _RES_CESEL_ID,
        "jerez_cesel",
        "Coste efectivo de servicios (CESEL) — Ayuntamiento de Jerez",
        "jerez_cesel",
        [
            ("url_template", f"{_BASE}/e-otrainfo/costeservicios/CESEL-{{year}}.xlsx"),
            ("granularity",  "annual"),
            ("year_from",    "2015"),
            ("year_to",      "2021"),
            # CESEL es XLSX, no PDF — usar FileDownloadFetcher real en producción.
            # Este resource actúa como placeholder; el fetcher_id apunta a PDF_TABLE
            # pero el handler webhook de CityDashboard sabe que CESEL viene como XLSX.
            # TODO(S14): separar en un resource con FILE_DOWNLOAD cuando se implemente S14.
        ],
    ),
]


def upgrade() -> None:
    conn = op.get_bind()

    # ── 1. Registrar fetcher PDF_TABLE ─────────────────────────────────────
    conn.execute(
        sa.text(
            "INSERT INTO opendata.fetcher (id, name, class_path, description) "
            "VALUES (:id, :code, :class_path, :desc) "
            "ON CONFLICT (name) DO NOTHING"
        ),
        {
            "id":         _FETCHER_ID,
            "code":       "PDF_TABLE",
            "class_path": "app.fetchers.pdf_table.PdfTableFetcher",
            "desc":       "Fetcher for PDFs: iterates year/month/quarter range and extracts tables with pdfplumber",
        },
    )

    # Obtener el UUID real (puede diferir si ya existía con otro ID)
    row = conn.execute(
        sa.text("SELECT id FROM opendata.fetcher WHERE name = 'PDF_TABLE'")
    ).fetchone()
    fetcher_uuid = str(row[0])

    # ── 2. Publicador (Ayuntamiento de Jerez) ─────────────────────────────
    pub_row = conn.execute(
        sa.text(
            "SELECT id FROM opendata.publisher WHERE acronimo = 'AJFRA' LIMIT 1"
        )
    ).fetchone()
    if pub_row:
        publisher_uuid = str(pub_row[0])
    else:
        publisher_uuid = str(uuid4())
        conn.execute(
            sa.text(
                "INSERT INTO opendata.publisher (id, nombre, acronimo, nivel, pais, "
                "comunidad_autonoma, provincia, municipio, portal_url) "
                "VALUES (:id, :nombre, :acronimo, :nivel, :pais, :ca, :prov, :mun, :url)"
            ),
            {
                "id":       publisher_uuid,
                "nombre":   "Ayuntamiento de Jerez de la Frontera",
                "acronimo": "AJFRA",
                "nivel":    "LOCAL",
                "pais":     "España",
                "ca":       "Andalucía",
                "prov":     "Cádiz",
                "mun":      "Jerez de la Frontera",
                "url":      "https://transparencia.jerez.es",
            },
        )

    # ── 3. Crear recursos ──────────────────────────────────────────────────
    for (res_id, name, desc, target_table, params) in _RESOURCES:
        conn.execute(
            sa.text(
                "INSERT INTO opendata.resource "
                "(id, name, description, target_table, fetcher_id, publisher_id, "
                " active, enable_load, load_mode) "
                "VALUES (:id, :name, :desc, :tt, :fid, :pid, true, false, 'replace') "
                "ON CONFLICT (name) DO NOTHING"
            ),
            {
                "id":   res_id,
                "name": name,
                "desc": desc,
                "tt":   target_table,
                "fid":  fetcher_uuid,
                "pid":  publisher_uuid,
            },
        )
        # Obtener UUID real del resource (por si ya existía)
        real_res = conn.execute(
            sa.text("SELECT id FROM opendata.resource WHERE name = :name"),
            {"name": name},
        ).fetchone()
        real_res_id = str(real_res[0])

        for key, value in params:
            conn.execute(
                sa.text(
                    "INSERT INTO opendata.resource_param (id, resource_id, key, value) "
                    "VALUES (:id, :rid, :key, :val) "
                    "ON CONFLICT DO NOTHING"
                ),
                {"id": str(uuid4()), "rid": real_res_id, "key": key, "val": value},
            )

    # ── 4. Aplicación suscriptora CityDashboard ───────────────────────────
    conn.execute(
        sa.text(
            "INSERT INTO opendata.application "
            "(id, name, description, subscribed_resources, active, "
            " webhook_url, webhook_secret, consumption_mode) "
            "VALUES (:id, :name, :desc, '[]'::jsonb, true, :url, :secret, 'webhook') "
            "ON CONFLICT (name) DO UPDATE SET "
            "  webhook_url = EXCLUDED.webhook_url, "
            "  consumption_mode = EXCLUDED.consumption_mode"
        ),
        {
            "id":     _APP_ID,
            "name":   "CityDashboard",
            "desc":   "Panel de Control Municipal — recibe KPIs financieros via webhook",
            "url":    "http://citydashboard_api:8015/webhooks/odmgr",
            "secret": "REPLACE_WITH_ODMGR_SECRET",
        },
    )


def downgrade() -> None:
    conn = op.get_bind()

    for (res_id, name, *_) in _RESOURCES:
        conn.execute(
            sa.text("DELETE FROM opendata.resource_param WHERE resource_id = "
                    "(SELECT id FROM opendata.resource WHERE name = :name)"),
            {"name": name},
        )
        conn.execute(
            sa.text("DELETE FROM opendata.resource WHERE name = :name"),
            {"name": name},
        )

    conn.execute(
        sa.text("DELETE FROM opendata.fetcher WHERE name = 'PDF_TABLE'")
    )
