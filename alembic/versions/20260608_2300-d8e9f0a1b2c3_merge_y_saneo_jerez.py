"""merge de cabezas + saneamiento de crawlers Web Tree de Jerez

Revision ID: d8e9f0a1b2c3
Revises: b4c5d6e7f8a9, c7d8e9f0a1b2
Create Date: 2026-06-08

Unifica las dos cabezas (colecciones + cadena §11/§12) y, de paso, sanea un
solapamiento real medido en producción:

El "Portal de Transparencia (censo documental)" (5db6263e) y el "crawler Web
Tree" (d835b782) rastrean el MISMO árbol de transparencia.jerez.es: los 1027
pathTemplate del censo están al 100% contenidos en los del crawler, que además
descubre 21 más. El censo como crawler separado es redundante (no aporta
descubrimiento; la variante 'Censo documental' es un MODO al promover, no un
crawler aparte). Acciones, todas reversibles (soft-delete / reasignación):

  1. Reasigna el único miembro del censo (FITUR anual, 1ca13a1e) al crawler
     genérico, para no perder esa promoción.
  2. Soft-delete del censo redundante (5db6263e) y de sus candidatos.
  3. Rellena el publisher (texto) del crawler, que estaba vacío pese a tener
     publisher_id de Jerez.

Idempotente: actúa por id y solo sobre filas aún no borradas; re-ejecutar o
aplicar en otra BD es no-op. Revertir: ver downgrade().
"""
from typing import Union, Sequence

from alembic import op


revision: str = 'd8e9f0a1b2c3'
down_revision: Union[str, Sequence[str], None] = ('b4c5d6e7f8a9', 'c7d8e9f0a1b2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CENSO = '5db6263e-8c1a-4c17-91ad-c30f8939e15e'      # crawler redundante (a retirar)
_CRAWLER = 'd835b782-eb44-4860-8f5f-af77a97b549a'    # crawler genérico (se conserva)
_HIJO_FITUR = '1ca13a1e-ffd7-4237-9522-89c46c7f01bb' # único miembro del censo
_JEREZ = 'Ayuntamiento de Jerez de la Frontera'


def upgrade() -> None:
    # 1) Conservar el miembro del censo reubicándolo bajo el crawler genérico.
    op.execute(f"""
        UPDATE opendata.resource SET parent_resource_id = '{_CRAWLER}'
        WHERE id = '{_HIJO_FITUR}' AND parent_resource_id = '{_CENSO}'
    """)
    # 2) Retirar (soft-delete) el censo redundante y sus candidatos.
    op.execute(f"""
        UPDATE opendata.resource SET deleted_at = now()
        WHERE id = '{_CENSO}' AND deleted_at IS NULL
    """)
    op.execute(f"""
        UPDATE opendata.resource_candidate SET deleted_at = now()
        WHERE crawler_resource_id = '{_CENSO}' AND deleted_at IS NULL
    """)
    # 3) Coherencia: el crawler tenía publisher_id de Jerez pero el campo texto
    #    vacío.
    op.execute(f"""
        UPDATE opendata.resource SET publisher = '{_JEREZ}'
        WHERE id = '{_CRAWLER}' AND (publisher IS NULL OR publisher = '')
    """)


def downgrade() -> None:
    op.execute(f"UPDATE opendata.resource_candidate SET deleted_at = NULL WHERE crawler_resource_id = '{_CENSO}'")
    op.execute(f"UPDATE opendata.resource SET deleted_at = NULL WHERE id = '{_CENSO}'")
    op.execute(f"UPDATE opendata.resource SET parent_resource_id = '{_CENSO}' WHERE id = '{_HIJO_FITUR}'")
