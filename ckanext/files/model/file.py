import copy
from datetime import datetime

import six
from sqlalchemy import Column, DateTime, UnicodeText
from sqlalchemy.dialects.postgresql import JSONB

from ckan.lib.dictization import table_dictize
from ckan.model.types import make_uuid

from .base import Base

if six.PY3:
    pass


def now():
    return datetime.utcnow()


class File(Base):  # type: ignore
    __tablename__ = "files_file"
    id = Column(UnicodeText, primary_key=True, default=make_uuid)
    name = Column(UnicodeText, nullable=False)
    storage = Column(UnicodeText, nullable=False)

    ctime = Column(DateTime, nullable=False, default=now)
    mtime = Column(DateTime)
    atime = Column(DateTime)

    storage_data = Column(JSONB, default=dict)
    plugin_data = Column(JSONB, default=dict)

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
        self.mtime = now()
