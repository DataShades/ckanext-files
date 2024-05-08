"""Types for the extension.

These bizarre definitions must remain here as long as Python2 is supported.

"""

import six
from sqlalchemy.sql.expression import Select
from werkzeug.datastructures import FileStorage as Upload

import ckan.plugins.toolkit as tk

CapabilityCluster = int
CapabilityUnit = int
TypedDict = lambda _name, _fields, **kwargs: type(_name, (dict,), {})  # type: ignore # noqa: E731
Declaration = None
Key = None
Any = None
IO = None
Iterable = None
PUploader = None
PResourceUploader = None
cast = lambda _type, _value: _value  # type: ignore # noqa: E731

if six.PY3:
    from typing import (  # pyright: ignore[reportConstantRedefinition]
        IO,
        Any,
        Iterable,
        cast,
    )

    from typing_extensions import NewType, TypedDict

    CapabilityCluster = NewType("CapabilityCluster", int)
    CapabilityUnit = NewType("CapabilityUnit", int)

    if tk.check_ckan_version("2.10"):
        from ckan.config.declaration import Declaration, Key
        from ckan.types import PResourceUploader, PUploader

__all__ = [
    "Upload",
    "CapabilityCluster",
    "CapabilityUnit",
    "TypedDict",
    "MinimalStorageData",
    "Key",
    "Declaration",
    "Any",
    "IO",
    "Select",
    "PUploader",
    "PResourceUploader",
    "cast",
    "Iterable",
]


MinimalStorageData = TypedDict(
    "MinimalStorageData",
    {"filename": str, "content_type": str, "size": int, "hash": str},
)
