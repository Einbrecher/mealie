"""add slot overlap penalty weight

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-14 17:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    op.add_column(
        "optimizer_config", sa.Column("slot_overlap_penalty_weight", sa.Float(), nullable=False, server_default="0.7")
    )


def downgrade():
    op.drop_column("optimizer_config", "slot_overlap_penalty_weight")
