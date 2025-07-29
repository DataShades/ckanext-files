"""update transfer history.

Revision ID: e1e5e203d76a
Revises: 565ef5eca492
Create Date: 2025-07-29 23:14:08.426318

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e1e5e203d76a"
down_revision = "565ef5eca492"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("files_transfer_history", "leave_date", new_column_name="at")
    op.add_column(
        "files_transfer_history",
        sa.Column("action", sa.Text(), nullable=False, server_default="transfer"),
    )

    op.create_index("idx_file_owner_owner", "files_owner", ["owner_type", "owner_id"])


def downgrade():
    op.alter_column("files_transfer_history", "at", new_column_name="leave_date")
    op.drop_column("files_transfer_history", "action")

    op.drop_index(
        "idx_file_owner_owner",
        "files_owner",
    )
