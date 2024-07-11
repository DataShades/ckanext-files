"""remove_path_rename_kind_add_stats.

Revision ID: 5851e09b7ca3
Revises: 2c5f1f90888c
Create Date: 2024-02-28 20:11:11.274864

"""

import os
from datetime import datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "5851e09b7ca3"
down_revision = "2c5f1f90888c"
branch_labels = None
depends_on = None

table = sa.table(
    "files_file",
    sa.column("id"),
    sa.column("last_access"),
    sa.column("path"),
    sa.column("atime"),
    sa.column("extras", JSONB),
)


def upgrade():
    bind = op.get_bind()

    op.add_column("files_file", sa.Column("plugin_data", JSONB, server_default="{}"))
    op.add_column("files_file", sa.Column("mtime", sa.DateTime()))
    op.add_column("files_file", sa.Column("atime", sa.DateTime()))
    op.alter_column("files_file", "uploaded_at", new_column_name="ctime")
    op.alter_column("files_file", "kind", new_column_name="storage")

    columns = [table.c.id, table.c.last_access, table.c.path, table.c.extras]
    stmt = sa.select(*columns)

    for id, last_access, path, extras in bind.execute(stmt):
        op.execute(
            sa.update(table)
            .values(
                atime=last_access,
                extras=dict(extras or {}, filename=os.path.basename(path)),
            )
            .where(table.c.id == id),
        )

    op.alter_column(
        "files_file",
        "extras",
        server_default="{}",
        new_column_name="storage_data",
    )
    op.drop_column("files_file", "last_access")
    op.drop_column("files_file", "path")


def downgrade():
    bind = op.get_bind()

    op.add_column(
        "files_file",
        sa.Column(
            "path",
            sa.UnicodeText,
            nullable=False,
            server_default="'/empty.data'",
        ),
    )
    op.add_column(
        "files_file",
        sa.Column(
            "last_access",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.alter_column("files_file", "storage", new_column_name="kind")
    op.alter_column("files_file", "ctime", new_column_name="uploaded_at")
    op.alter_column(
        "files_file",
        "storage_data",
        server_default=None,
        new_column_name="extras",
    )

    columns = [table.c.id, table.c.atime, table.c.extras]
    stmt = sa.select(*columns)

    for id, atime, extras in bind.execute(stmt):
        extras_copy = dict(extras)
        path = extras_copy.pop("filename", None)
        if not path:
            continue
        op.execute(
            sa.update(table)
            .values(
                last_access=atime or datetime.now(),  # noqa: DTZ005
                extras=extras_copy,
                path=path,
            )
            .where(table.c.id == id),
        )

    op.drop_column("files_file", "atime")
    op.drop_column("files_file", "mtime")
    op.drop_column("files_file", "plugin_data")
