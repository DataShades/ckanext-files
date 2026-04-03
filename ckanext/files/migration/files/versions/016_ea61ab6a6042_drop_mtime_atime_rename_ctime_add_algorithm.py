"""empty message.

Revision ID: ea61ab6a6042
Revises: 6e3c2aa192f6
Create Date: 2026-04-03 16:11:40.353869

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "ea61ab6a6042"
down_revision = "6e3c2aa192f6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("files_file", sa.Column("algorithm", sa.Text(), nullable=False, server_default=""))
    op.alter_column("files_file", "ctime", new_column_name="created")
    op.drop_column("files_file", "mtime")
    op.drop_column("files_file", "atime")


def downgrade():
    op.add_column(
        "files_file", sa.Column("atime", postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True)
    )
    op.add_column(
        "files_file", sa.Column("mtime", postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True)
    )
    op.alter_column("files_file", "created", new_column_name="ctime")
    op.drop_column("files_file", "algorithm")
