"""Types for the extension."""

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
    Response,
    Validator,
    ValidatorFactory,
)

FileOperation = Literal["show", "update", "delete"]
"""Operation that performed on file."""

OwnerOperation = Literal["show", "update", "delete", "file_transfer", "file_scan"]
"""Operation that performed on owner."""

Uploadable = Union[
    FileStorage,
    "tempfile.SpooledTemporaryFile[Any]",
    TextIOWrapper,
    bytes,
    bytearray,
    BinaryIO,
]
"""Content that can be converted into Upload."""


class PUploadStream(Protocol):
    def read(self, size: Any = ..., /) -> bytes: ...

    def __iter__(self) -> Iterator[bytes]: ...


class PSeekableStream(PUploadStream):
    def tell(self) -> int: ...

    def seek(self, offset: int, whence: int = 0) -> int: ...


class PTask(Protocol):
    def __call__(self, result: Any, idx: int, prev: Any) -> Any: ...


__all__ = [
    "Context",
    "Validator",
    "ValidatorFactory",
    "FlattenKey",
    "FlattenErrorDict",
    "FlattenDataDict",
    "Declaration",
    "FileOperation",
    "OwnerOperation",
    "Key",
    "PTask",
    "Response",
]
