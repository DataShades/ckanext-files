"""empty message.

Revision ID: b4b6ff46cd13
Revises: ea61ab6a6042
Create Date: 2026-04-03 16:38:46.405174

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b4b6ff46cd13"
down_revision = "ea61ab6a6042"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("files_transfer_history", "item_type")
    op.alter_column("files_transfer_history", "item_id", new_column_name="file_id")

    op.drop_column("files_owner", "item_type")
    op.alter_column("files_owner", "item_id", new_column_name="file_id")
    op.create_primary_key("files_owner_pkey", "files_owner", ["file_id"])

    op.create_foreign_key(
        "files_owner_file_id_fkey", "files_owner", "files_file", ["file_id"], ["id"], ondelete="CASCADE"
    )

    op.create_foreign_key(
        "files_transfer_history_owner_file_id_fkey",
        "files_transfer_history",
        "files_owner",
        ["file_id"],
        ["file_id"],
        ondelete="CASCADE",
    )


def downgrade():
    op.drop_constraint("files_transfer_history_owner_file_id_fkey", "files_transfer_history", type_="foreignkey")
    op.alter_column("files_transfer_history", "file_id", new_column_name="item_id")
    op.add_column("files_transfer_history", sa.Column("item_type", sa.TEXT(), autoincrement=False, nullable=False))
    op.create_index("idx_item", "files_transfer_history", ["item_id", "item_type"], unique=False)

    op.drop_constraint("files_owner_file_id_fkey", "files_owner", type_="foreignkey")

    op.add_column("files_owner", sa.Column("item_type", sa.TEXT(), autoincrement=False, nullable=False))
    op.alter_column("files_owner", "file_id", new_column_name="item_id")
    op.drop_constraint("files_owner_pkey", "files_owner")
    op.create_primary_key("files_owner_pkey", "files_owner", ["item_id", "item_type"])

    op.create_foreign_key(
        "files_transfer_history_owner_file_id_fkey",
        "files_transfer_history",
        "files_owner",
        ["item_id", "item_type"],
        ["item_id", "item_type"],
    )
