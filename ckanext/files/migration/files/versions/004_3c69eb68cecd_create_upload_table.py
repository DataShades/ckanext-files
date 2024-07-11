"""create upload table.

Revision ID: 3c69eb68cecd
Revises: 5851e09b7ca3
Create Date: 2024-03-03 21:53:32.955167

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "3c69eb68cecd"
down_revision = "5851e09b7ca3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "files_upload",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("storage", sa.Text, nullable=False),
        sa.Column(
            "initialized_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("upload_data", JSONB, server_default="{}"),
    )


def downgrade():
    op.drop_table("files_upload")
