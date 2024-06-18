from __future__ import annotations

import copy
from datetime import datetime
from typing import Any, Literal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, foreign, relationship

from ckan.lib.dictization import table_dictize
from ckan.model.types import make_uuid

from ckanext.files import utils

from .base import Base, now
from .owner import Owner

foreign: Any


class Multipart(Base):  # type: ignore
    __table__ = sa.Table(
        "files_multipart",
        Base.metadata,
        sa.Column("id", sa.UnicodeText, primary_key=True, default=make_uuid),
        sa.Column("name", sa.UnicodeText, nullable=False),
        sa.Column("location", sa.Text, nullable=False, default=""),
        sa.Column("content_type", sa.Text, nullable=False, default=""),
        sa.Column("size", sa.Integer, nullable=False, default=0),
        sa.Column("hash", sa.Text, nullable=False, default=""),
        sa.Column("storage", sa.Text, nullable=False),
        sa.Column(
            "ctime",
            sa.DateTime(timezone=True),
            default=now,
            server_default=sa.func.now(),
        ),
        sa.Column("storage_data", JSONB, default=dict, server_default="{}"),
        sa.Column("plugin_data", JSONB, default=dict, server_default="{}"),
    )

    id: Mapped[str]

    name: Mapped[str]
    storage: Mapped[str]

    ctime: Mapped[datetime]
    size: Mapped[int]
    content_type: Mapped[str]
    hash: Mapped[str]

    storage_data: Mapped[dict[str, Any]]
    plugin_data: Mapped[dict[str, Any]]

    owner_info: Mapped[Owner | None] = relationship(
        Owner,
        primaryjoin=sa.and_(
            Owner.item_id == foreign(__table__.c.id),
            Owner.item_type == "multipart",
        ),
        single_parent=True,
        uselist=False,
        cascade="delete, delete-orphan",
        lazy="joined",
    )  # type: ignore

    @property
    def owner(self) -> Any | None:
        owner = self.owner_info
        if not owner:
            return None

        return utils.get_owner(owner.owner_type, owner.owner_id)

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        if not self.id:
            self.id = make_uuid()

    def dictize(self, context: Any) -> dict[str, Any]:
        result = table_dictize(self, context)
        result["storage_data"] = copy.deepcopy(result["storage_data"])

        if self.owner_info:
            result["owner_type"] = self.owner_info.owner_type
            result["owner_id"] = self.owner_info.owner_id
            result["pinned"] = self.owner_info.pinned
        else:
            result["owner_type"] = None
            result["owner_id"] = None
            result["pinned"] = False

        plugin_data = result.pop("plugin_data")
        if context.get("include_plugin_data"):
            result["plugin_data"] = copy.deepcopy(plugin_data)

        return result

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
                target = target.setdefault(part, {})
                if not isinstance(target, dict):
                    raise TypeError(part)
        target.update(patch)

        setattr(self, prop, data)
        return data
