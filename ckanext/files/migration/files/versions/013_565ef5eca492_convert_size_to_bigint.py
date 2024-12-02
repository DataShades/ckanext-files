"""convert size to bigint

Revision ID: 565ef5eca492
Revises: d19094d45a0f
Create Date: 2024-12-02 02:40:53.449550

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "565ef5eca492"
down_revision = "d19094d45a0f"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        table_name="files_file",
        column_name="size",
        nullable=False,
        server_default="0",
        type_=sa.BigInteger,
    )
    op.alter_column(
        table_name="files_multipart",
        column_name="size",
        nullable=False,
        server_default="0",
        type_=sa.BigInteger,
    )


def downgrade():
    op.alter_column(
        table_name="files_file",
        column_name="size",
        nullable=False,
        server_default="0",
        type_=sa.Integer,
    )
    op.alter_column(
        table_name="files_multipart",
        column_name="size",
        nullable=False,
        server_default="0",
        type_=sa.Integer,
    )
