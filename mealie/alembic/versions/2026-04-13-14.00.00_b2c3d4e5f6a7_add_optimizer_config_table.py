"""add optimizer config table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-13 14:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

import mealie.db.migration_types

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    op.create_table(
        "optimizer_config",
        sa.Column("id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("group_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("household_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("overlap_weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("pantry_utilization_weight", sa.Float(), nullable=False, server_default="0.6"),
        sa.Column("pantry_urgency_weight", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("protein_diversity_weight", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("category_balance_weight", sa.Float(), nullable=False, server_default="0.3"),
        sa.Column("rating_weight", sa.Float(), nullable=False, server_default="0.2"),
        sa.Column("prep_time_budget_minutes", sa.Integer(), nullable=True),
        sa.Column(
            "perishable_label_keywords",
            sa.JSON(),
            nullable=False,
            server_default='["vegetable","fruit","dairy","egg","meat","poultry","fish","seafood","herb"]',
        ),
        sa.Column(
            "shelf_stable_label_keywords",
            sa.JSON(),
            nullable=False,
            server_default='["spice","grain","pasta","canned","dried","frozen","oil","vinegar","condiment"]',
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("household_id", name="optimizer_config_household_key"),
    )
    op.create_index(op.f("ix_optimizer_config_group_id"), "optimizer_config", ["group_id"], unique=False)
    op.create_index(op.f("ix_optimizer_config_household_id"), "optimizer_config", ["household_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_optimizer_config_household_id"), table_name="optimizer_config")
    op.drop_index(op.f("ix_optimizer_config_group_id"), table_name="optimizer_config")
    op.drop_table("optimizer_config")
