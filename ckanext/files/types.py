"""Types for the extension.

These bizarre definitions must remain here as long as Python2 is supported.

"""

import six
from werkzeug.datastructures import FileStorage as Upload

CapabilityCluster = int
CapabilityUnit = int
TypedDict = lambda _name, _fields, **kwargs: type(_name, (dict,), {})  # type: ignore # noqa: E731


if six.PY3:
    from typing_extensions import NewType, TypedDict

    CapabilityCluster = NewType("CapabilityCluster", int)
    CapabilityUnit = NewType("CapabilityUnit", int)


__all__ = [
    "Upload",
    "CapabilityCluster",
    "CapabilityUnit",
    "TypedDict",
    "MinimalStorageData",
]


MinimalStorageData = TypedDict(
    "MinimalStorageData",
    {"content_type": str, "size": int, "hash": str},
)
