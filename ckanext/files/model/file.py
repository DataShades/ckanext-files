import copy

import six
import sqlalchemy as sa
from sqlalchemy import Column, DateTime, UnicodeText
from sqlalchemy.dialects.postgresql import JSONB

from ckan.lib.dictization import table_dictize
from ckan.model.types import make_uuid

from .base import Base, now

from ckanext.files import types  # isort: skip # noqa: F401

if six.PY3:
    from typing import Any  # isort: skip # noqa: F401


class File(Base):  # type: ignore
    __tablename__ = "files_file"
    id = Column(UnicodeText, primary_key=True, default=make_uuid)
    name = Column(UnicodeText, nullable=False)
    storage = Column(UnicodeText, nullable=False)

    ctime = Column(DateTime, nullable=False, default=now, server_default=sa.func.now())
    mtime = Column(DateTime)
    atime = Column(DateTime)

    storage_data = Column(JSONB, default=dict, server_default="{}")
    plugin_data = Column(JSONB, default=dict, server_default="{}")
    completed = Column(sa.Boolean, default=False, server_default="false")

    def __init__(self, **kwargs):
        # type: (**types.Any) -> None
        super(File, self).__init__(**kwargs)
        if not self.id:
            self.id = make_uuid()

    def dictize(self, context):
        # type: (Any) -> dict[str, Any]

        result = table_dictize(self, context)
        result["storage_data"] = copy.deepcopy(result["storage_data"])

        plugin_data = result.pop("plugin_data")
        if context.get("include_plugin_data"):
            result["plugin_data"] = copy.deepcopy(plugin_data)

        return result

    def touch(self):
        self.mtime = now()

    def access(self):
        self.atime = now()
