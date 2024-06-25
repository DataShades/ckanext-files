"""Types for the extension.

"""

from __future__ import annotations

from typing import Any, Iterator, Literal, Protocol

from ckan.config.declaration import Declaration, Key
from ckan.types import (
    Context,
    FlattenDataDict,
    FlattenErrorDict,
    FlattenKey,
    Validator,
    ValidatorFactory,
)

AuthOperation = Literal["show", "update", "delete", "file_transfer"]


class UploadStream(Protocol):
    def read(self, size: Any = ..., /) -> bytes: ...

    def __iter__(self) -> Iterator[bytes]: ...


__all__ = [
    "Context",
    "Validator",
    "ValidatorFactory",
    "FlattenKey",
    "FlattenErrorDict",
    "FlattenDataDict",
    "AuthOperation",
    "Declaration",
    "Key",
]
