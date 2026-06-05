"""Perfiles (presets) de especie: tabla fetcher_preset + resource.preset_id.

La particularización con nombre (p. ej. 'PLACSP CODICE' sobre 'Feeds ATOM/RSS')
deja de ser una fila-variante del catálogo y pasa a ser una entidad anidada bajo
la especie, elegida por cada recurso.
"""
from typing import Union, Sequence
from alembic import op

revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS opendata.fetcher_preset (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            fetcher_id UUID NOT NULL REFERENCES opendata.fetcher(id) ON DELETE CASCADE,
            code VARCHAR(100) NOT NULL,
            description TEXT,
            params JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP,
            deleted_at TIMESTAMP,
            CONSTRAINT uq_fetcher_preset_code UNIQUE (fetcher_id, code)
        )
    """)
    op.execute(
        "ALTER TABLE opendata.resource ADD COLUMN IF NOT EXISTS preset_id UUID "
        "REFERENCES opendata.fetcher_preset(id) ON DELETE SET NULL"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE opendata.resource DROP COLUMN IF EXISTS preset_id")
    op.execute("DROP TABLE IF EXISTS opendata.fetcher_preset")
