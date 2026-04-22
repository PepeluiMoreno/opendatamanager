"""initial — schema completo consolidado

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-23

Migración única que crea el esquema opendata al completo.
Reemplaza todas las migraciones anteriores.
"""
from typing import Union, Sequence
from uuid import uuid4
import json

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = '0001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEFAULT_SETTINGS = [
    ("max_concurrent_processes", 3,
     "Maximum number of fetcher processes that can run simultaneously"),
    ("default_fetch_timeout", 120,
     "Default HTTP timeout in seconds for fetcher requests"),
    ("log_retention_days", 30,
     "Number of days to keep execution log files on disk"),
    ("execution_retention_days", 90,
     "Number of days to keep execution records in the database"),
    ("auto_run_on_startup", False,
     "Run all active resources automatically when the backend starts"),
    ("max_pages_per_run", 0,
     "Global cap on paginated fetcher pages per run (0 = unlimited)"),
    ("notify_on_failure", False,
     "Send a notification when a resource execution fails"),
    ("default_page_size", 100,
     "Default page size used by paginated fetchers if not specified in params"),
]

_FETCHER_ID   = "d4000001-0000-0000-0000-000000000001"
_RES_PMP_ID   = "d4000002-0000-0000-0000-000000000001"
_RES_MOR_ID   = "d4000003-0000-0000-0000-000000000001"
_RES_DEUDA_ID = "d4000004-0000-0000-0000-000000000001"
_RES_CESEL_ID = "d4000005-0000-0000-0000-000000000001"
_APP_ID       = "d4000006-0000-0000-0000-000000000001"
_BASE = "https://transparencia.jerez.es/infopublica/economica"

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
        ],
    ),
]


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS opendata;")

    # ── fetcher ────────────────────────────────────────────────────────────
    op.create_table(
        'fetcher',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(50), nullable=False, unique=True),
        sa.Column('class_path', sa.String(255)),
        sa.Column('description', sa.Text),
        schema='opendata',
    )

    # ── type_fetcher_params ────────────────────────────────────────────────
    op.create_table(
        'type_fetcher_params',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('fetcher_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('opendata.fetcher.id')),
        sa.Column('param_name', sa.String(100), nullable=False),
        sa.Column('required', sa.Boolean, default=True),
        sa.Column('data_type', sa.String(20), default='string'),
        sa.Column('default_value', postgresql.JSONB),
        sa.Column('enum_values', postgresql.JSONB, nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('group', sa.String(100), nullable=True),
        schema='opendata',
    )

    # ── publisher ──────────────────────────────────────────────────────────
    op.create_table(
        'publisher',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('nombre', sa.String(200), nullable=False),
        sa.Column('acronimo', sa.String(30), nullable=True),
        sa.Column('nivel', sa.String(30), nullable=False),
        sa.Column('pais', sa.String(100), nullable=False, server_default='España'),
        sa.Column('comunidad_autonoma', sa.String(100), nullable=True),
        sa.Column('portal_url', sa.String(500), nullable=True),
        sa.Column('email', sa.String(200), nullable=True),
        sa.Column('telefono', sa.String(50), nullable=True),
        sa.Column('provincia', sa.String(100), nullable=True),
        sa.Column('municipio', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        schema='opendata',
    )

    # ── resource ───────────────────────────────────────────────────────────
    op.create_table(
        'resource',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text),
        sa.Column('publisher', sa.String(200), nullable=True),
        sa.Column('publisher_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('opendata.publisher.id'), nullable=True),
        sa.Column('target_table', sa.String(100)),
        sa.Column('fetcher_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('opendata.fetcher.id')),
        sa.Column('active', sa.Boolean, default=True),
        sa.Column('enable_load', sa.Boolean, default=False),
        sa.Column('load_mode', sa.String(20), default='replace'),
        sa.Column('schedule', sa.String(100), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        schema='opendata',
    )

    # ── resource_param ─────────────────────────────────────────────────────
    op.create_table(
        'resource_param',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('opendata.resource.id', ondelete='CASCADE'), nullable=False),
        sa.Column('key', sa.String(100), nullable=False),
        sa.Column('value', sa.Text, nullable=False),
        sa.Column('is_external', sa.Boolean, nullable=False, server_default='false'),
        schema='opendata',
    )

    # ── application ────────────────────────────────────────────────────────
    op.create_table(
        'application',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text),
        sa.Column('models_path', sa.String(255), nullable=False),
        sa.Column('subscribed_resources', postgresql.JSONB, nullable=False,
                  server_default='[]'),
        sa.Column('active', sa.Boolean, default=True),
        sa.Column('webhook_url', sa.String(500)),
        sa.Column('webhook_secret', sa.String(100)),
        sa.Column('consumption_mode', sa.String(20), nullable=False,
                  server_default='webhook'),
        schema='opendata',
    )

    # ── field_metadata ─────────────────────────────────────────────────────
    op.create_table(
        'field_metadata',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('table_name', sa.String(100), nullable=False),
        sa.Column('field_name', sa.String(100), nullable=False),
        sa.Column('label', sa.String(255)),
        sa.Column('help_text', sa.Text),
        sa.Column('placeholder', sa.String(255)),
        schema='opendata',
    )

    # ── resource_execution ─────────────────────────────────────────────────
    op.create_table(
        'resource_execution',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('opendata.resource.id'), nullable=False),
        sa.Column('started_at', sa.DateTime, default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime),
        sa.Column('status', sa.String(20)),
        sa.Column('total_records', sa.Integer),
        sa.Column('records_loaded', sa.Integer),
        sa.Column('staging_path', sa.String(500)),
        sa.Column('error_message', sa.Text),
        sa.Column('execution_params', postgresql.JSONB, nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('pause_requested', sa.Boolean(), nullable=False,
                  server_default='false'),
        sa.Column('active_seconds', sa.Integer(), nullable=True,
                  server_default='0'),
        schema='opendata',
    )

    # ── dataset ────────────────────────────────────────────────────────────
    op.create_table(
        'dataset',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('opendata.resource.id'), nullable=False),
        sa.Column('execution_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('opendata.resource_execution.id')),
        sa.Column('major_version', sa.Integer, nullable=False),
        sa.Column('minor_version', sa.Integer, nullable=False),
        sa.Column('patch_version', sa.Integer, nullable=False),
        sa.Column('schema_json', postgresql.JSONB, nullable=False),
        sa.Column('data_path', sa.String(500), nullable=False),
        sa.Column('record_count', sa.Integer),
        sa.Column('checksum', sa.String(64)),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('label', sa.String(100), nullable=True),
        schema='opendata',
    )

    # ── dataset_subscription ───────────────────────────────────────────────
    op.create_table(
        'dataset_subscription',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('application_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('opendata.application.id'), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('opendata.resource.id'), nullable=False),
        sa.Column('pinned_version', sa.String(20)),
        sa.Column('auto_upgrade', sa.String(20), default='patch'),
        sa.Column('current_version', sa.String(20)),
        sa.Column('notified_at', sa.DateTime),
        schema='opendata',
    )

    # ── application_notification ───────────────────────────────────────────
    op.create_table(
        'application_notification',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('application_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('opendata.application.id'), nullable=False),
        sa.Column('dataset_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('opendata.dataset.id')),
        sa.Column('sent_at', sa.DateTime, default=sa.func.now()),
        sa.Column('status_code', sa.Integer),
        sa.Column('response_body', sa.Text),
        sa.Column('error_message', sa.Text),
        schema='opendata',
    )

    # ── app_config ─────────────────────────────────────────────────────────
    op.create_table(
        'app_config',
        sa.Column('key', sa.String(100), primary_key=True),
        sa.Column('value', postgresql.JSONB, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True),
        schema='opendata',
    )

    # ── derived_dataset_config ─────────────────────────────────────────────
    op.create_table(
        'derived_dataset_config',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('source_resource_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('opendata.resource.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('target_name', sa.String(100), nullable=False),
        sa.Column('key_field', sa.String(100), nullable=False),
        sa.Column('extract_fields', postgresql.JSONB, nullable=False,
                  server_default='[]'),
        sa.Column('merge_strategy', sa.String(20), nullable=False,
                  server_default='upsert'),
        sa.Column('enabled', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()')),
        schema='opendata',
    )

    # ── derived_dataset_entry ──────────────────────────────────────────────
    op.create_table(
        'derived_dataset_entry',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('config_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('opendata.derived_dataset_config.id',
                                ondelete='CASCADE'), nullable=False),
        sa.Column('key_value', sa.String(500), nullable=False),
        sa.Column('data', postgresql.JSONB, nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('now()')),
        sa.UniqueConstraint('config_id', 'key_value',
                            name='uq_derived_entry_config_key'),
        schema='opendata',
    )

    # ── seed: app_config ───────────────────────────────────────────────────
    conn = op.get_bind()
    for key, value, description in DEFAULT_SETTINGS:
        conn.execute(
            sa.text(
                "INSERT INTO opendata.app_config (key, value, description, updated_at) "
                "VALUES (:key, CAST(:value AS jsonb), :desc, now()) "
                "ON CONFLICT (key) DO NOTHING"
            ),
            {"key": key, "value": json.dumps(value), "desc": description},
        )

    # ── seed: fetcher PDF_TABLE ────────────────────────────────────────────
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

    row = conn.execute(
        sa.text("SELECT id FROM opendata.fetcher WHERE name = 'PDF_TABLE'")
    ).fetchone()
    fetcher_uuid = str(row[0])

    # ── seed: publisher Jerez ──────────────────────────────────────────────
    publisher_uuid = str(uuid4())
    conn.execute(
        sa.text(
            "INSERT INTO opendata.publisher (id, nombre, acronimo, nivel, pais, "
            "comunidad_autonoma, provincia, municipio, portal_url) "
            "VALUES (:id, :nombre, :acronimo, :nivel, :pais, :ca, :prov, :mun, :url) "
            "ON CONFLICT DO NOTHING"
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

    actual_pub = conn.execute(
        sa.text("SELECT id FROM opendata.publisher WHERE acronimo = 'AJFRA' LIMIT 1")
    ).fetchone()
    publisher_uuid = str(actual_pub[0])

    # ── seed: recursos Jerez ───────────────────────────────────────────────
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

    # ── seed: aplicación CityDashboard ─────────────────────────────────────
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
    op.drop_table('derived_dataset_entry', schema='opendata')
    op.drop_table('derived_dataset_config', schema='opendata')
    op.drop_table('app_config', schema='opendata')
    op.drop_table('application_notification', schema='opendata')
    op.drop_table('dataset_subscription', schema='opendata')
    op.drop_table('dataset', schema='opendata')
    op.drop_table('resource_execution', schema='opendata')
    op.drop_table('field_metadata', schema='opendata')
    op.drop_table('application', schema='opendata')
    op.drop_table('resource_param', schema='opendata')
    op.drop_table('resource', schema='opendata')
    op.drop_table('publisher', schema='opendata')
    op.drop_table('type_fetcher_params', schema='opendata')
    op.drop_table('fetcher', schema='opendata')
    op.execute("DROP SCHEMA IF EXISTS opendata;")
