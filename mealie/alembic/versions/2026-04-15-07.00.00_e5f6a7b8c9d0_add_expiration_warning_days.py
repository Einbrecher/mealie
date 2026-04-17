"""add expiration warning days

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-15 07:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e5f6a7b8c9d0"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    op.add_column(
        "optimizer_config", sa.Column("expiration_warning_days", sa.Integer(), nullable=False, server_default="3")
    )


def downgrade():
    op.drop_column("optimizer_config", "expiration_warning_days")
