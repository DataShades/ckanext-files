from __future__ import annotations

from typing import Any

import ckan.plugins.toolkit as tk
from ckan.types import Context, FlattenDataDict, FlattenErrorDict, FlattenKey

from ckanext.files import utils


def files_into_upload(value: Any) -> utils.Upload:
    """Convert value into Upload object"""
    try:
        return utils.make_upload(value)

    except TypeError as err:
        msg = "Unsupported source type: {}".format(err)
        raise tk.Invalid(msg) from err

    except ValueError as err:
        msg = "Wrong file: {}".format(err)
        raise tk.Invalid(msg) from err


def files_parse_filesize(value: Any) -> int:
    """Convert human-readable filesize into an integer."""

    if isinstance(value, int):
        return value

    try:
        return utils.parse_filesize(value)
    except ValueError as err:
        raise tk.Invalid("Wrong filesize string: {}".format(value)) from err


def files_ensure_name(name_field: str):
    """Apply to Upload to guess filename where `name_field` is empty."""

    def validator(
        key: FlattenKey,
        data: FlattenDataDict,
        errors: FlattenErrorDict,
        context: Context,
    ) -> None:
        name_key = key[:-1] + (name_field,)
        if data.get(name_key):
            return

        if name := data[key].filename:
            data[name_key] = name
            return

        raise tk.Invalid(f"Name is missing and cannot be deduced from {key[-1]}")

    return validator
