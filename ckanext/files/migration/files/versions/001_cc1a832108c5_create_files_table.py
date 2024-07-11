"""Create files table.

Revision ID: cc1a832108c5
Revises:
Create Date: 2021-09-21 13:02:25.731642

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "cc1a832108c5"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "files_file",
        sa.Column("id", sa.UnicodeText, primary_key=True),
        sa.Column("name", sa.UnicodeText, nullable=False),
        sa.Column("path", sa.UnicodeText, nullable=False),
        sa.Column("kind", sa.UnicodeText, nullable=False),
        sa.Column(
            "uploaded_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.Column("extras", JSONB),
    )


def downgrade():
    op.drop_table("files_file")
