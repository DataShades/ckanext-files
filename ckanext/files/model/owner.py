import six
import sqlalchemy as sa

import ckan.plugins.toolkit as tk
from ckan.lib.dictization import table_dictize
from ckan.model.types import make_uuid

from .base import Base

from ckanext.files import types  # isort: skip # noqa: F401

if six.PY3:
    from typing import Any  # isort: skip # noqa: F401


class Owner(Base):  # type: ignore
    __tablename__ = "files_owner"
    id = sa.Column(sa.Text, primary_key=True, default=make_uuid)

    item_id = sa.Column(sa.Text, nullable=False)
    item_type = sa.Column(sa.Text, nullable=False)
    owner_id = sa.Column(sa.Text, nullable=False)
    owner_type = sa.Column(sa.Text, nullable=False)
    access = sa.Column(sa.Text, nullable=False, default="full")

    sa.UniqueConstraint(item_id, item_type, owner_id, owner_type)

    def dictize(self, context):
        # type: (Any) -> dict[str, Any]
        return table_dictize(self, context)

    @classmethod
    def owners_of(cls, id, type):
        # type: (str, str) -> types.Select
        """List owners of the given item."""
        selectable = cls if tk.check_ckan_version("2.9") else [cls]
        return sa.select(selectable).where(
            sa.and_(cls.item_type == type, cls.item_id == id),
        )

    @classmethod
    def owned_by(cls, id, type):
        # type: (str, str) -> types.Select
        """List records with given owner."""
        selectable = cls if tk.check_ckan_version("2.9") else [cls]
        return sa.select(selectable).where(
            sa.and_(cls.owner_type == type, cls.owner_id == id),
        )
