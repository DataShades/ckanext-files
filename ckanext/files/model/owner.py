from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import Mapped

from ckan.lib.dictization import table_dictize
from ckan.types import Context

from .base import Base


class Owner(Base):  # type: ignore
    """Model with details about current owner of an item.

    Keyword Args:
        item_id (str): ID of the owned object
        item_type (str): type of the owned object
        owner_id (str): ID of the owner
        owner_type (str): Type of the owner
        pinned (bool): is ownership protected from transfer

    Example:
        ```python
        owner = Owner(
            item_id=file.id,
            item_type="file",
            owner_id=user.id,
            owner_type="user,
        )
        ```
    """

    __table__ = sa.Table(
        "files_owner",
        Base.metadata,
        sa.Column("item_id", sa.Text, primary_key=True),
        sa.Column("item_type", sa.Text, primary_key=True),
        sa.Column("owner_id", sa.Text, nullable=False),
        sa.Column("owner_type", sa.Text, nullable=False),
        sa.Column("pinned", sa.Boolean, default=False, nullable=False),
    )
    item_id: Mapped[str]
    item_type: Mapped[str]
    owner_id: Mapped[str]
    owner_type: Mapped[str]
    pinned: Mapped[bool]

    def dictize(self, context: Context):
        return table_dictize(self, context)
