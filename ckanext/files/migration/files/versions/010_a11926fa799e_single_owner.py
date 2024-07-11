"""single owner.

Revision ID: a11926fa799e
Revises: c7081d7f02e8
Create Date: 2024-06-09 18:18:13.987236

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a11926fa799e"
down_revision = "c7081d7f02e8"
branch_labels = None
depends_on = None

table = sa.table("files_owner", sa.column("owner_type"))


def upgrade():
    op.drop_column("files_owner", "access")
    op.drop_column("files_owner", "id")
    op.add_column(
        "files_owner",
        sa.Column("pinned", sa.Boolean, nullable=False, server_default="false"),
    )

    op.create_primary_key("files_owner_pkey", "files_owner", ["item_id", "item_type"])
    op.drop_constraint(
        "files_owner_item_id_item_type_owner_id_owner_type_key",
        "files_owner",
    )


def downgrade():
    op.drop_column("files_owner", "pinned")
    op.add_column(
        "files_owner",
        sa.Column("access", sa.Text, nullable=False, server_default="full"),
    )
    op.drop_constraint("files_owner_pkey", "files_owner")
    op.add_column(
        "files_owner",
        sa.Column(
            "id",
            sa.Text(),
            primary_key=True,
            server_default=sa.text("uuid_in(md5(random()::text)::cstring)"),
        ),
    )
    op.create_primary_key("files_owner_pkey", "files_owner", ["id"])
    op.alter_column("files_owner", "id", server_default=None)

    op.create_unique_constraint(
        "files_owner_item_id_item_type_owner_id_owner_type_key",
        "files_owner",
        [
            "item_id",
            "item_type",
            "owner_id",
            "owner_type",
        ],
    )
