"""add pantry use priority

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-13 15:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    op.add_column("pantry_items", sa.Column("use_priority", sa.String(), nullable=False, server_default="auto"))
    op.create_check_constraint(
        "pantry_item_use_priority_check", "pantry_items", "use_priority IN ('auto', 'high', 'low')"
    )


def downgrade():
    op.drop_constraint("pantry_item_use_priority_check", "pantry_items", type_="check")
    op.drop_column("pantry_items", "use_priority")
