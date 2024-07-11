"""Add file last_access field.

Revision ID: 2c5f1f90888c
Revises: cc1a832108c5
Create Date: 2024-01-27 12:47:35.568291

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "2c5f1f90888c"
down_revision = "cc1a832108c5"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "files_file",
        sa.Column(
            "last_access",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade():
    op.drop_column("files_file", "last_access")
