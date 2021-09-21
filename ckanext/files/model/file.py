from __future__ import annotations

import datetime


from sqlalchemy import Column, UnicodeText, DateTime
from sqlalchemy.dialects.postgresql import JSONB

import ckan.plugins.toolkit as tk
from ckan.model.types import make_uuid
from ckan.lib.dictization import table_dictize
from .base import Base


class File(Base):
    __tablename__ = "files_file"
    id = Column(UnicodeText, primary_key=True, default=make_uuid)
    name = Column(UnicodeText, nullable=False, unique=True)
    url = Column(UnicodeText, nullable=False)
    kind = Column(UnicodeText, nullable=False)
    uploaded_at = Column(
        DateTime, nullable=False, default=datetime.datetime.utcnow
    )
    extras = Column(JSONB)

    def dictize(self, context):
        result = table_dictize(self, context)
        result["url"] = tk.h.url_for_static(result["url"])
        return result
