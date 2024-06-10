from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

import ckan.plugins.toolkit as tk
from ckan import model

from ckanext.files import utils

owner_getters = utils.Registry[Callable[[str], Any]]({})

Base = tk.BaseModel


def now():
    return datetime.now(timezone.utc)


def get_owner(owner_type: str, owner_id: str):
    for mapper in model.registry.mappers:
        cls = mapper.class_
        if hasattr(cls, "__table__") and cls.__table__.name == owner_type:
            return model.Session.get(cls, owner_id)

    raise TypeError(owner_type)
