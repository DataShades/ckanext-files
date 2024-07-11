"""use timestamp with timezone.

Revision ID: c7081d7f02e8
Revises: d94bacc491e4
Create Date: 2024-06-02 17:55:53.431773

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c7081d7f02e8"
down_revision = "d94bacc491e4"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("files_file", "ctime", type_=sa.DateTime(timezone=True))
    op.alter_column("files_file", "mtime", type_=sa.DateTime(timezone=True))
    op.alter_column("files_file", "atime", type_=sa.DateTime(timezone=True))

    op.alter_column("files_multipart", "ctime", type_=sa.DateTime(timezone=True))


def downgrade():
    op.alter_column("files_file", "ctime", type_=sa.DateTime(timezone=False))
    op.alter_column("files_file", "mtime", type_=sa.DateTime(timezone=False))
    op.alter_column("files_file", "atime", type_=sa.DateTime(timezone=False))

    op.alter_column("files_multipart", "ctime", type_=sa.DateTime(timezone=False))
