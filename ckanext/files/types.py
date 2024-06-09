"""Types for the extension.
"""

from __future__ import annotations

from typing import Any, Literal, Protocol, TypeVar

__all__ = ["PFileModel", "TFileModel"]


class PFileModel(Protocol):
    location: str
    size: int
    content_type: str
    hash: str
    storage_data: dict[str, Any]


TFileModel = TypeVar("TFileModel", bound=PFileModel)

AuthOperation = Literal["show", "update", "delete"]
