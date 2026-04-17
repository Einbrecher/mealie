"""add onboarding completed

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-04-15 08:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f6a7b8c9d0e1"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    op.add_column(
        "optimizer_config", sa.Column("onboarding_completed", sa.Boolean(), nullable=False, server_default="false")
    )


def downgrade():
    op.drop_column("optimizer_config", "onboarding_completed")
