"""Types for the extension.
"""

from __future__ import annotations

from typing import Any, Protocol, TypeVar

from .utils import AuthOperation

__all__ = ["PFileModel", "TFileModel", "AuthOperation"]


class PFileModel(Protocol):
    location: str
    size: int
    content_type: str
    hash: str
    storage_data: dict[str, Any]


TFileModel = TypeVar("TFileModel", bound=PFileModel)
