from __future__ import annotations

import copy
import secrets
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped

from ckan import model
from ckan.lib.dictization import table_dictize
from ckan.types import AlchemySession, Context

from .base import Base, now


def link_id():
    return secrets.token_urlsafe(100)


class Link(Base):  # type: ignore
    __table__ = sa.Table(
        "files_link",
        Base.metadata,
        sa.Column("id", sa.Text, primary_key=True, default=link_id),
        sa.Column("type", sa.Text, nullable=False),
        sa.Column("ctime", sa.DateTime(timezone=True), nullable=False, default=now),
        sa.Column("atime", sa.DateTime(timezone=True)),
        sa.Column("etime", sa.DateTime(timezone=True)),
        sa.Column("counter", sa.Integer),
        sa.Column("data", JSONB, default=dict),
    )
    id: Mapped[str]
    type: Mapped[str]
    ctime: Mapped[datetime]
    atime: Mapped[datetime | None]
    etime: Mapped[datetime | None]
    counter: Mapped[int | None]
    data: Mapped[dict[str, Any]]

    def dictize(self, context: Context):
        result = table_dictize(self, context)
        result["data"] = copy.deepcopy(result["data"])
        return result

    @classmethod
    def consume(cls, link_id: str, session: AlchemySession = model.Session):
        link = session.get(cls, link_id)
        if not link:
            return None

        link.atime = now()
        if link.counter is not None:
            link.counter -= 1
            if link.counter < 1:
                session.delete(link)
                return None

        if link.etime is not None and link.etime < now():
            session.delete(link)
            return None

        session.commit()
        return link
