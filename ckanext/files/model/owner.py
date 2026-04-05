from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, relationship

from ckan.lib.dictization import table_dictize
from ckan.model.vocabulary import TYPE_CHECKING
from ckan.types import Context

if TYPE_CHECKING:
    from .file import FilesFile


from .base import Base


class FilesOwner(Base):
    """Model with details about current owner of an item.

    Keyword Args:
        file_id (str): ID of the owned object
        owner_id (str): ID of the owner
        owner_type (str): Type of the owner
        pinned (bool): is ownership protected from transfer

    Example:
        ```python
        owner = Owner(
            file_id=file.id,
            owner_id=user.id,
            owner_type="user,
        )
        ```
    """

    __table__ = sa.Table(
        "files_owner",
        Base.metadata,
        sa.Column("file_id", sa.Text, primary_key=True),
        sa.Column("owner_id", sa.Text, nullable=False),
        sa.Column("owner_type", sa.Text, nullable=False),
        sa.Column("pinned", sa.Boolean, default=False, nullable=False),
        sa.Index("idx_file_owner_owner", "owner_type", "owner_id", unique=False),
        sa.ForeignKeyConstraint(
            ["file_id"],
            ["files_file.id"],
            "files_owner_file_id_fkey",
            ondelete="CASCADE",
        ),
    )
    file_id: Mapped[str]
    owner_id: Mapped[str]
    owner_type: Mapped[str]
    pinned: Mapped[bool]

    files: Mapped[list[FilesFile]] = relationship("FilesFile", back_populates="owner")

    def dictize(self, context: Context):
        return table_dictize(self, context)

    def select_history(self):
        """Returns a select statement to fetch ownership history."""
        from .transfer_history import TransferHistory  # noqa: PLC0415

        return (
            sa.select(TransferHistory)
            .join(FilesOwner)
            .where(
                TransferHistory.file_id == self.file_id,
            )
        )
