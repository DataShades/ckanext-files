"""add access column to owner table.

Revision ID: 76fdef67f479
Revises: 64ca007bf3eb
Create Date: 2024-03-18 16:17:35.734318

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "76fdef67f479"
down_revision = "64ca007bf3eb"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "files_owner",
        sa.Column("access", sa.Text, nullable=False, server_default="full"),
    )


def downgrade():
    op.drop_column("files_owner", "access")
