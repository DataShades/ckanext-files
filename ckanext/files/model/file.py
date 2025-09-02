from __future__ import annotations

import copy
from datetime import datetime
from typing import Any, Literal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, foreign, relationship

from ckan.lib.dictization import table_dictize
from ckan.model.types import make_uuid

from .base import Base, now
from .owner import FilesOwner

foreign: Any


class FilesFile(Base):
    """Model with file details.

    Keyword Args:
        name (str): name shown to users
        location (str): location of the file inside storage
        content_type (str): MIMEtype
        size (int): size in bytes
        hash (str): checksum
        storage (str): storage that contains the file
        ctime (datetime): date of creation
        mtime (datetime | None): date of the last update
        atime (datetime | None): date of last access(unstable)
        storage_data (dict[str, Any]): additional data set by storage
        plugin_data (dict[str, Any]): additional data set by plugins

    Example:
        ```python
        file = File(
            name="file.txt",
            location="relative/path/safe-name.txt",
            content_type="text/plain",
            size=100,
            hash="abc123",
            storage="default",
        )
        ```
    """

    __table__ = sa.Table(
        "files_file",
        Base.metadata,
        sa.Column("id", sa.UnicodeText, primary_key=True, default=make_uuid),
        sa.Column("name", sa.UnicodeText, nullable=False),
        sa.Column("location", sa.Text, nullable=False),
        sa.Column(
            "content_type",
            sa.Text,
            nullable=False,
            default="application/octet-stream",
        ),
        sa.Column("size", sa.Integer, nullable=False, default=0),
        sa.Column("hash", sa.Text, nullable=False, default=""),
        sa.Column("storage", sa.Text, nullable=False),
        sa.Column(
            "ctime",
            sa.DateTime(timezone=True),
            nullable=False,
            default=now,
            server_default=sa.func.now(),
        ),
        sa.Column("mtime", sa.DateTime(timezone=True)),
        sa.Column("atime", sa.DateTime(timezone=True)),
        sa.Column("storage_data", JSONB, default=dict, server_default="{}"),
        sa.Column("plugin_data", JSONB, default=dict, server_default="{}"),
    )

    id: Mapped[str]

    name: Mapped[str]
    location: Mapped[str]
    content_type: Mapped[str]
    size: Mapped[int]
    hash: Mapped[str]

    storage: Mapped[str]

    ctime: Mapped[datetime]
    mtime: Mapped[datetime | None]
    atime: Mapped[datetime | None]

    storage_data: Mapped[dict[str, Any]]
    plugin_data: Mapped[dict[str, Any]]

    owner: Mapped[FilesOwner | None] = relationship(  # type: ignore
        FilesOwner,
        primaryjoin=sa.and_(
            FilesOwner.item_id == foreign(__table__.c.id),
            FilesOwner.item_type == "file",
        ),
        single_parent=True,
        uselist=False,
        cascade="delete, delete-orphan",
        lazy="joined",
    )

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        if not self.id:
            self.id = make_uuid()

    def dictize(self, context: Any) -> dict[str, Any]:
        result = table_dictize(self, context)
        result["storage_data"] = copy.deepcopy(result["storage_data"])

        if self.owner:
            result["owner_type"] = self.owner.owner_type
            result["owner_id"] = self.owner.owner_id
            result["pinned"] = self.owner.pinned

        else:
            result["owner_type"] = None
            result["owner_id"] = None
            result["pinned"] = False

        plugin_data = result.pop("plugin_data")
        if context.get("include_plugin_data"):
            result["plugin_data"] = copy.deepcopy(plugin_data)

        return result

    def touch(
        self,
        access: bool = True,
        modification: bool = False,
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

        target: Any = data
        if dict_path:
            for part in dict_path:
                target = target.setdefault(part, {})  # pyright: ignore[reportUnknownVariableType]
                if not isinstance(target, dict):
                    raise TypeError(part)

        target.update(patch)

        setattr(self, prop, data)
        return data

    @classmethod
    def by_location(cls, location: str, storage: str):
        return sa.select(cls).where(
            cls.location == location,
            cls.storage == storage,
        )
