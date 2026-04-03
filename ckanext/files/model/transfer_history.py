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
        file_id (str): ID of the owned object
        owner_id (str): ID of the owner
        owner_type (str): Type of the owner
        leave_date (datetime): date of ownership transfer to a different owner
        actor (str | None): user who initiated ownership transfer

    Example:
        ```python
        record = TransferHistory(
            file_id=file.id,
            owner_id=prev_owner.owner_id,
            owner_type=prev_owner.owner_type,
        )
        ```
    """

    __table__ = sa.Table(
        "files_transfer_history",
        Base.metadata,
        sa.Column("id", sa.Text, primary_key=True, default=make_uuid),
        sa.Column("file_id", sa.Text, nullable=False),
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
        sa.ForeignKeyConstraint(
            ["file_id"],
            ["files_owner.file_id"],
            "files_transfer_history_owner_file_id_fkey",
            ondelete="CASCADE",
        ),
    )
    id: Mapped[str]
    file_id: Mapped[str]
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
            file_id=owner.file_id,
            owner_id=owner.owner_id,
            owner_type=owner.owner_type,
            actor=actor,
        )
