"""Types for the extension.

"""

from __future__ import annotations

import tempfile
from io import TextIOWrapper
from typing import Any, BinaryIO, Iterator, Literal, Protocol, Union

from werkzeug.datastructures import FileStorage

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

Uploadable = Union[
    FileStorage,
    "tempfile.SpooledTemporaryFile[Any]",
    TextIOWrapper,
    bytes,
    bytearray,
    BinaryIO,
]


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
