"""add pantry items table

Revision ID: a1b2c3d4e5f6
Revises: 4395a04f7784
Create Date: 2026-04-13 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

import mealie.db.migration_types

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision: str | None = "4395a04f7784"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    op.create_table(
        "pantry_items",
        sa.Column("id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("group_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("household_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("food_id", mealie.db.migration_types.GUID(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("is_staple", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("assume_enough", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("quantity", sa.Float(), nullable=True),
        sa.Column("unit_id", mealie.db.migration_types.GUID(), nullable=True),
        sa.Column("expiration_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
        sa.ForeignKeyConstraint(["food_id"], ["ingredient_foods.id"]),
        sa.ForeignKeyConstraint(["unit_id"], ["ingredient_units.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("household_id", "food_id", name="pantry_item_household_food_key"),
        sa.CheckConstraint("food_id IS NOT NULL OR name IS NOT NULL", name="pantry_item_food_or_name_check"),
    )
    op.create_index(op.f("ix_pantry_items_group_id"), "pantry_items", ["group_id"], unique=False)
    op.create_index(op.f("ix_pantry_items_household_id"), "pantry_items", ["household_id"], unique=False)
    op.create_index(op.f("ix_pantry_items_food_id"), "pantry_items", ["food_id"], unique=False)
    op.create_index(op.f("ix_pantry_items_created_at"), "pantry_items", ["created_at"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_pantry_items_created_at"), table_name="pantry_items")
    op.drop_index(op.f("ix_pantry_items_food_id"), table_name="pantry_items")
    op.drop_index(op.f("ix_pantry_items_household_id"), table_name="pantry_items")
    op.drop_index(op.f("ix_pantry_items_group_id"), table_name="pantry_items")
    op.drop_table("pantry_items")
