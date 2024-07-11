"""empty message.

Revision ID: d19094d45a0f
Revises: 6a6ea2472155
Create Date: 2024-06-18 13:23:04.625122

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "d19094d45a0f"
down_revision = "6a6ea2472155"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("files_file", "content_type", nullable=False)
    op.alter_column("files_file", "size", nullable=False)
    op.alter_column("files_file", "hash", nullable=False)


def downgrade():
    op.alter_column("files_file", "hash", nullable=True)
    op.alter_column("files_file", "size", nullable=True)
    op.alter_column("files_file", "content_type", nullable=True)
