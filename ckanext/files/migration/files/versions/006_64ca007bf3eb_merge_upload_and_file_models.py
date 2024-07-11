"""merge upload and file models.

Revision ID: 64ca007bf3eb
Revises: 2fbd30a1b364
Create Date: 2024-03-07 21:01:21.133717

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "64ca007bf3eb"
down_revision = "2fbd30a1b364"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("files_upload")
    op.add_column(
        "files_file",
        sa.Column("completed", sa.Boolean, server_default="false"),
    )


def downgrade():
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
    op.drop_column("files_file", "completed")
