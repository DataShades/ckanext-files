"""Types for the extension.

"""

from __future__ import annotations

from typing import Literal

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
