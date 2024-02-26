import six

import datetime


from sqlalchemy import Column, UnicodeText, DateTime
from sqlalchemy.dialects.postgresql import JSONB

import ckan.plugins.toolkit as tk
from ckan.model.types import make_uuid
from ckan.lib.dictization import table_dictize
from .base import Base

if six.PY3:
    from typing import Any


class File(Base):  # type: ignore
    __tablename__ = "files_file"
    id = Column(UnicodeText, primary_key=True, default=make_uuid)
    name = Column(UnicodeText, nullable=False)
    path = Column(UnicodeText, nullable=False)
    kind = Column(UnicodeText, nullable=False)
    uploaded_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    last_access = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    extras = Column(JSONB)

    def dictize(self, context):
        # type: (Any) -> dict[str, Any]
        result = table_dictize(self, context)
        result["url"] = tk.h.url_for("files.get_file", file_id=self.id, qualified=True)
        return result
