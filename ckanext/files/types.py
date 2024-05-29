"""Types for the extension.
"""

from typing_extensions import TypedDict
from werkzeug.datastructures import FileStorage as Upload

__all__ = [
    "Upload",
    "MinimalStorageData",
]


MinimalStorageData = TypedDict(
    "MinimalStorageData",
    {"filename": str, "content_type": str, "size": int, "hash": str},
)
