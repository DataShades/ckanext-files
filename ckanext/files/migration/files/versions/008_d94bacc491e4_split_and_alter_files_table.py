"""alter files table.

Revision ID: d94bacc491e4
Revises: 76fdef67f479
Create Date: 2024-05-29 22:19:22.535787

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "d94bacc491e4"
down_revision = "76fdef67f479"
branch_labels = None
depends_on = None

table = sa.table(
    "files_file",
    sa.column("id"),
    sa.column("name"),
    sa.column("storage"),
    sa.column("storage_data", JSONB),
    sa.column("plugin_data", JSONB),
    sa.column("location"),
    sa.column("content_type"),
    sa.column("size"),
    sa.column("ctime"),
    sa.column("hash"),
    sa.column("completed"),
)
owner_table = sa.table(
    "files_owner",
    sa.column("item_id"),
    sa.column("item_type"),
)


def upgrade():
    bind = op.get_bind()

    multipart_table = op.create_table(
        "files_multipart",
        sa.Column("id", sa.UnicodeText, primary_key=True),
        sa.Column("name", sa.UnicodeText, nullable=False),
        sa.Column("location", sa.UnicodeText, nullable=False, server_default=""),
        sa.Column("storage", sa.Text, nullable=False),
        sa.Column("ctime", sa.DateTime, server_default=sa.func.now()),
        sa.Column("size", sa.Integer, nullable=False, server_default="0"),
        sa.Column("content_type", sa.Text, nullable=False, server_default=""),
        sa.Column("hash", sa.Text, nullable=False, server_default=""),
        sa.Column("storage_data", JSONB, server_default="{}"),
        sa.Column("plugin_data", JSONB, server_default="{}"),
    )

    stmt = sa.select(
        table.c.id,
        table.c.name,
        table.c.storage,
        table.c.ctime,
        table.c.storage_data,
        table.c.plugin_data,
    ).where(table.c.completed == sa.false())

    for id, name, storage, ctime, data, plugin_data in bind.execute(stmt):
        data["location"] = data.pop("filename")
        content_type = data.pop("content_type", "application/octet-stream")
        size = data.pop("size", 0)
        hash = data.pop("hash", "")

        bind.execute(
            sa.insert(multipart_table).values(
                id=id,
                name=name,
                storage=storage,
                ctime=ctime,
                content_type=content_type,
                size=size,
                hash=hash,
                storage_data=data,
                plugin_data=plugin_data,
            ),
        )
        bind.execute(
            sa.update(owner_table)
            .values(item_type="multipart")
            .where(owner_table.c.item_id == id),
        )

    bind.execute(sa.delete(table).where(table.c.completed == sa.false()))

    op.add_column("files_file", sa.Column("location", sa.Text))
    op.add_column(
        "files_file",
        sa.Column("content_type", sa.Text, server_default="application/octet-stream"),
    )
    op.add_column("files_file", sa.Column("size", sa.Integer, server_default="0"))
    op.add_column("files_file", sa.Column("hash", sa.Text, server_default=""))
    op.drop_column("files_file", "completed")

    stmt = sa.select(table.c.id, table.c.storage_data)
    for id, data in bind.execute(stmt):
        location = data.pop("filename")
        content_type = data.pop("content_type")
        size = data.pop("size")
        hash = data.pop("hash")

        bind.execute(
            sa.update(table)
            .values(
                location=location,
                storage_data=data,
                content_type=content_type,
                size=size,
                hash=hash,
            )
            .where(table.c.id == id),
        )

    op.alter_column("files_file", "location", nullable=False)


def downgrade():
    bind = op.get_bind()

    stmt = sa.select(
        table.c.id,
        table.c.storage_data,
        table.c.location,
        table.c.content_type,
        table.c.size,
        table.c.hash,
    )
    for id, data, location, content_type, size, hash in bind.execute(stmt):
        data["filename"] = location
        data["content_type"] = content_type
        data["size"] = size
        data["hash"] = hash
        bind.execute(sa.update(table).values(storage_data=data).where(table.c.id == id))

    op.drop_column("files_file", "location")
    op.drop_column("files_file", "content_type")
    op.drop_column("files_file", "size")
    op.drop_column("files_file", "hash")
    op.add_column(
        "files_file",
        sa.Column("completed", sa.Boolean, server_default="false"),
    )
    bind.execute(sa.update(table).values(completed=sa.true()))

    op.drop_table("files_multipart")
