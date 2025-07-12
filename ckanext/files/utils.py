"""Internal utilities of the extension.

Do not use this module outside of the extension and do not import any other
internal module except for config, types and exceptions. Only independent tools
are stored here, to avoid import cycles.

"""

from __future__ import annotations

import logging
from typing import Any, Callable, Iterable, TypeVar, cast

import file_keeper as fk
import jwt
from sqlalchemy.orm import Mapper

import ckan.plugins.toolkit as tk
from ckan import model
from ckan.lib.api_token import _get_algorithm, _get_secret  # type: ignore

from ckanext.files import types

log = logging.getLogger(__name__)

T = TypeVar("T")

SAMPLE_SIZE = 1024 * 2


owner_getters = fk.Registry[Callable[[str], Any]]({})


def is_supported_type(content_type: str, supported: Iterable[str]) -> bool:
    """Check whether content_type it matches supported types."""
    maintype, subtype = content_type.split("/")
    desired = {content_type, maintype, subtype}
    return any(st in desired for st in supported)


def get_owner(owner_type: str, owner_id: str):
    if getter := owner_getters.get(owner_type):
        return getter(owner_id)

    owner_model = "group" if owner_type == "organization" else owner_type
    mappers: Iterable[Mapper]
    if tk.check_ckan_version("2.11"):
        mappers = model.registry.mappers
    else:
        mappers = cast(
            "Iterable[Mapper]",
            tk.BaseModel._sa_registry.mappers
            | model.User._sa_class_manager.registry.mappers,  # type: ignore
        )

    for mapper in mappers:
        cls = mapper.class_
        table = getattr(cls, "__table__", None)
        if table is None:
            table = getattr(mapper, "local_table", None)

        if table is not None and table.name == owner_model:
            return model.Session.get(cls, owner_id)

    log.warning("Unknown owner type %s with ID %s", owner_type, owner_id)
    return None


def encode_token(data: dict[str, Any]) -> str:
    return jwt.encode(data, _get_secret(encode=True), algorithm=_get_algorithm())


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, _get_secret(encode=False), algorithms=[_get_algorithm()])


class ContextCache:
    key = "files_cache"

    def __init__(self, context: types.Context):
        self.session = context.get("session", model.Session)
        self.cache = cast("dict[str, Any]", context).setdefault(self.key, {})

    def invalidate(self, type: str, id: str):
        self.cache.setdefault(type, {}).pop(id, None)

    def bucket(self, type: str) -> dict[str, Any]:
        return self.cache.setdefault(type, {})

    def set(self, type: str, id: str, value: T) -> T:
        bucket = self.bucket(type)
        bucket[id] = value
        return value

    def get(self, type: str, id: str, compute: Callable[[], T]) -> T:
        bucket = self.bucket(type)
        if id not in bucket:
            bucket[id] = compute()

        return bucket[id]

    def get_model(self, type: str, id: str, model_class: type[T]) -> T | None:
        return self.get(type, id, lambda: self.session.get(model_class, id))
