"""drop multipart table.

Revision ID: 6e3c2aa192f6
Revises: e1e5e203d76a
Create Date: 2025-08-30 01:38:23.393215

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "6e3c2aa192f6"
down_revision = "e1e5e203d76a"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("idx_files_file_location_in_storage", "files_file", ["storage", "location"], unique=True)

    op.drop_table("files_multipart")


def downgrade():
    op.drop_index("idx_files_file_location_in_storage", "files_file")
    op.create_table(
        "files_multipart",
        sa.Column("id", sa.UnicodeText, primary_key=True),
        sa.Column("name", sa.UnicodeText, nullable=False),
        sa.Column("location", sa.Text, nullable=False, default=""),
        sa.Column("content_type", sa.Text, nullable=False, default=""),
        sa.Column("size", sa.Integer, nullable=False, default=0),
        sa.Column("hash", sa.Text, nullable=False, default=""),
        sa.Column("storage", sa.Text, nullable=False),
        sa.Column(
            "ctime",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("storage_data", JSONB, default=dict, server_default="{}"),
        sa.Column("plugin_data", JSONB, default=dict, server_default="{}"),
    )
