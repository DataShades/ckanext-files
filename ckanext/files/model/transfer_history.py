from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, backref, relationship

from ckan.lib.dictization import table_dictize
from ckan.model.types import make_uuid
from ckan.types import Context

from .base import Base, now
from .owner import FilesOwner


class TransferHistory(Base):
    """Model for tracking ownership history of the file.

    Keyword Args:
        item_id (str): ID of the owned object
        item_type (str): type of the owned object
        owner_id (str): ID of the owner
        owner_type (str): Type of the owner
        leave_date (datetime): date of ownership transfer to a different owner
        actor (str | None): user who initiated ownership transfer

    Example:
        ```python
        record = TransferHistory(
            item_id=file.id,
            item_type="file",
            owner_id=prev_owner.owner_id,
            owner_type=prev_owner.owner_type,
        )
        ```
    """

    __table__ = sa.Table(
        "files_transfer_history",
        Base.metadata,
        sa.Column("id", sa.Text, primary_key=True, default=make_uuid),
        sa.Column("item_id", sa.Text, nullable=False),
        sa.Column("item_type", sa.Text, nullable=False),
        sa.Column("owner_id", sa.Text, nullable=False),
        sa.Column("owner_type", sa.Text, nullable=False),
        sa.Column(
            "at",
            sa.DateTime(timezone=True),
            default=now,
            nullable=False,
        ),
        sa.Column("action", sa.Text, nullable=False, default="transfer"),
        sa.Column("actor", sa.Text, nullable=False),
        sa.Index("idx_item", "item_id", "item_type"),
        sa.ForeignKeyConstraint(
            ["item_id", "item_type"],
            ["files_owner.item_id", "files_owner.item_type"],
        ),
    )
    id: Mapped[str]
    item_id: Mapped[str]
    item_type: Mapped[str]
    owner_id: Mapped[str]
    owner_type: Mapped[str]
    at: Mapped[datetime]
    action: Mapped[str]
    actor: Mapped[str]

    current: Mapped[FilesOwner] = relationship(  # type: ignore
        FilesOwner,
        backref=backref("history", cascade="delete, delete-orphan"),
    )

    def dictize(self, context: Context):
        return table_dictize(self, context)

    @classmethod
    def from_owner(cls, owner: FilesOwner, actor: str = ""):
        return cls(
            item_id=owner.item_id,
            item_type=owner.item_type,
            owner_id=owner.owner_id,
            owner_type=owner.owner_type,
            actor=actor,
        )
