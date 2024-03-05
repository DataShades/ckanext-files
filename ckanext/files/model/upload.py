import copy

import six
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from ckan.lib.dictization import table_dictize
from ckan.model.types import make_uuid

from .base import Base, now

if six.PY3:
    from typing import Any  # isort: skip # noqa: F401


class Upload(Base):  # type: ignore
    __tablename__ = "files_upload"
    id = sa.Column(sa.Text, primary_key=True, default=make_uuid)
    name = sa.Column(sa.Text, nullable=False)
    storage = sa.Column(sa.Text, nullable=False)

    initialized_at = sa.Column(sa.DateTime, nullable=False, default=now)
    upload_data = sa.Column(JSONB, default=dict)

    def dictize(self, context):
        # type: (Any) -> dict[str, Any]

        result = table_dictize(self, context)
        result["upload_data"] = copy.deepcopy(result["upload_data"])

        return result
