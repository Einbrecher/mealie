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


def upgrade() -> None:
    with op.batch_alter_table("pantry_items") as batch_op:
        batch_op.add_column(
            sa.Column(
                "use_priority",
                sa.String(),
                nullable=False,
                server_default="auto",
            )
        )
        batch_op.create_check_constraint(
            "pantry_item_use_priority_check",
            "use_priority IN ('auto', 'high', 'low')",
        )


def downgrade() -> None:
    with op.batch_alter_table("pantry_items") as batch_op:
        batch_op.drop_constraint(
            "pantry_item_use_priority_check",
            type_="check",
        )
        batch_op.drop_column("use_priority")
