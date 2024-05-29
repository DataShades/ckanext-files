from __future__ import annotations

import copy
from datetime import datetime
from typing import Any, Literal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped

from ckan.lib.dictization import table_dictize
from ckan.model.types import make_uuid

from .base import Base, now


class File(Base):  # type: ignore
    __table__ = sa.Table(
        "files_file",
        Base.metadata,
        sa.Column("id", sa.UnicodeText, primary_key=True, default=make_uuid),
        sa.Column("name", sa.UnicodeText, nullable=False),
        sa.Column("storage", sa.UnicodeText, nullable=False),
        sa.Column(
            "ctime",
            sa.DateTime,
            nullable=False,
            default=now,
            server_default=sa.func.now(),
        ),
        sa.Column("mtime", sa.DateTime),
        sa.Column("atime", sa.DateTime),
        sa.Column("storage_data", JSONB, default=dict, server_default="{}"),
        sa.Column("plugin_data", JSONB, default=dict, server_default="{}"),
        sa.Column("completed", sa.Boolean, default=False, server_default="false"),
    )

    id: Mapped[str]

    name: Mapped[str]
    storage: Mapped[str]

    ctime: Mapped[datetime]
    mtime: Mapped[datetime | None]
    atime: Mapped[datetime | None]

    storage_data: Mapped[dict[str, Any]]
    plugin_data: Mapped[dict[str, Any]]

    completed: Mapped[bool]

    def __init__(self, **kwargs: Any):
        super(File, self).__init__(**kwargs)
        if not self.id:
            self.id = make_uuid()

    def dictize(self, context: Any) -> dict[str, Any]:
        result = table_dictize(self, context)
        result["storage_data"] = copy.deepcopy(result["storage_data"])

        plugin_data = result.pop("plugin_data")
        if context.get("include_plugin_data"):
            result["plugin_data"] = copy.deepcopy(plugin_data)

        return result

    def touch(
        self,
        access: bool = True,
        modification: bool = True,
        moment: datetime | None = None,
    ):
        if not moment:
            moment = now()

        if access:
            self.atime = moment

        if modification:
            self.mtime = moment

    def patch_data(
        self,
        patch: dict[str, Any],
        dict_path: list[str] | None = None,
        prop: Literal["storage_data", "plugin_data"] = "plugin_data",
    ) -> dict[str, Any]:
        data: dict[str, Any] = copy.deepcopy(getattr(self, prop))

        target: dict[str, Any] | Any = data
        if dict_path:
            for part in dict_path:
                target = target.setdefault(part, {})
                if not isinstance(target, dict):
                    raise TypeError(part)
        target.update(patch)

        setattr(self, prop, data)
        return data

    @classmethod
    def by_location(cls, location, storage=None):
        # type: (str, str | None) -> sa.sql.Select
        stmt = sa.select(cls).where(
            cls.storage_data["filename"].astext == location,
        )

        if storage:
            stmt = stmt.where(cls.storage == storage)

        return stmt
