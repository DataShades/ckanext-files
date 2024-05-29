from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import Mapped

from ckan.lib.dictization import table_dictize
from ckan.model.types import make_uuid

from ckanext.files import types

from .base import Base


class Owner(Base):  # type: ignore
    ACCESS_FULL = "full"

    __table__ = sa.Table(
        "files_owner",
        Base.metadata,
        sa.Column("id", sa.Text, primary_key=True, default=make_uuid),
        sa.Column("item_id", sa.Text, nullable=False),
        sa.Column("item_type", sa.Text, nullable=False),
        sa.Column("owner_id", sa.Text, nullable=False),
        sa.Column("owner_type", sa.Text, nullable=False),
        sa.Column("access", sa.Text, nullable=False, default=ACCESS_FULL),
        sa.UniqueConstraint("item_id", "item_type", "owner_id", "owner_type"),
    )
    id: Mapped[str]

    item_id: Mapped[str]
    item_type: Mapped[str]
    owner_id: Mapped[str]
    owner_type: Mapped[str]
    access: Mapped[str]

    def dictize(self, context):
        # type: (Any) -> dict[str, Any]
        return table_dictize(self, context)

    @classmethod
    def owners_of(cls, id: str, type: str) -> types.Select:
        """List owners of the given item."""
        return sa.select(cls).where(
            sa.and_(cls.item_type == type, cls.item_id == id),
        )

    @classmethod
    def owned_by(cls, id: str, type: str) -> types.Select:
        # type: (str, str) -> types.Select
        """List records with given owner."""
        return sa.select(cls).where(
            sa.and_(cls.owner_type == type, cls.owner_id == id),
        )
