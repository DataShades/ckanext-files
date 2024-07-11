"""create transfer history table.

Revision ID: 6a6ea2472155
Revises: a11926fa799e
Create Date: 2024-06-16 16:23:27.102126

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6a6ea2472155"
down_revision = "a11926fa799e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "files_transfer_history",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("item_id", sa.Text, nullable=False),
        sa.Column("item_type", sa.Text, nullable=False),
        sa.Column("owner_id", sa.Text, nullable=False),
        sa.Column("owner_type", sa.Text, nullable=False),
        sa.Column(
            "leave_date",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("actor", sa.Text, nullable=False),
        sa.Index("idx_item", "item_id", "item_type"),
        sa.ForeignKeyConstraint(
            ["item_id", "item_type"],
            ["files_owner.item_id", "files_owner.item_type"],
        ),
    )


def downgrade():
    op.drop_table("files_transfer_history")
