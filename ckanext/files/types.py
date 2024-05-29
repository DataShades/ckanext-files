"""Types for the extension.

These bizarre definitions must remain here as long as Python2 is supported.

"""

from typing import IO, Any, Iterable, cast

from flask import Response
from sqlalchemy.sql.expression import Select
from typing_extensions import Literal, NewType, TypedDict
from werkzeug.datastructures import FileStorage as Upload

from ckan.config.declaration import Declaration, Key
from ckan.types import PResourceUploader, PUploader

CapabilityCluster = NewType("CapabilityCluster", int)
CapabilityUnit = NewType("CapabilityUnit", int)

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
    "Literal",
    "Response",
]


MinimalStorageData = TypedDict(
    "MinimalStorageData",
    {"filename": str, "content_type": str, "size": int, "hash": str},
)
