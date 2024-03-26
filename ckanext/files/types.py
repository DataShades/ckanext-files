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

if six.PY3:
    from typing import IO, Any  # pyright: ignore[reportConstantRedefinition]

    from typing_extensions import NewType, TypedDict

    CapabilityCluster = NewType("CapabilityCluster", int)
    CapabilityUnit = NewType("CapabilityUnit", int)

    if tk.check_ckan_version("2.10"):
        from ckan.config.declaration import Declaration, Key

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
]


MinimalStorageData = TypedDict(
    "MinimalStorageData",
    {"filename": str, "content_type": str, "size": int, "hash": str},
)
