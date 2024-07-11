"""create owner table.

Revision ID: 2fbd30a1b364
Revises: 3c69eb68cecd
Create Date: 2024-03-07 13:53:22.621465

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "2fbd30a1b364"
down_revision = "3c69eb68cecd"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "files_owner",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("item_id", sa.Text(), nullable=False),
        sa.Column("item_type", sa.Text(), nullable=False),
        sa.Column("owner_id", sa.Text(), nullable=False),
        sa.Column("owner_type", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "item_id",
            "item_type",
            "owner_id",
            "owner_type",
            name="files_owner_item_id_item_type_owner_id_owner_type_key",
        ),
    )


def downgrade():
    op.drop_table("files_owner")
