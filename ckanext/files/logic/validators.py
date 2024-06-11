from __future__ import annotations

from typing import Any

import ckan.plugins.toolkit as tk
from ckan import authz
from ckan.types import Context, FlattenDataDict, FlattenErrorDict, FlattenKey

from ckanext.files import utils
from ckanext.files.shared import File


def files_into_upload(value: Any) -> utils.Upload:
    """Convert value into Upload object"""
    try:
        return utils.make_upload(value)

    except TypeError as err:
        msg = f"Unsupported source type: {err}"
        raise tk.Invalid(msg) from err

    except ValueError as err:
        msg = f"Wrong file: {err}"
        raise tk.Invalid(msg) from err


def files_parse_filesize(value: Any) -> int:
    """Convert human-readable filesize into an integer."""

    if isinstance(value, int):
        return value

    try:
        return utils.parse_filesize(value)
    except ValueError as err:
        msg = f"Wrong filesize string: {value}"
        raise tk.Invalid(msg) from err


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

        msg = f"Name is missing and cannot be deduced from {key[-1]}"
        raise tk.Invalid(msg)

    return validator


def files_file_id_exists(value: Any, context: Context):
    """Verify that file ID exists."""
    file = context["session"].get(File, value)
    if not file:
        msg = "File does not exist"
        raise tk.Invalid(msg)

    return value


def files_file_content_type(*supported_types: str):
    """Verify that file ID exists."""

    def validator(value: Any, context: Context):
        file = context["session"].get(File, value)
        if not file:
            msg = "File does not exist"
            raise tk.Invalid(msg)

        actual = file.content_type
        if utils.is_supported_type(actual, supported_types):
            return value

        expected = ", ".join(supported_types)
        msg = (
            f"Type {actual} is not supported."
            + f" Use one of the following types: {expected}"
        )
        raise tk.Invalid(msg)

    return validator


def files_transfer_ownership(owner_type: str, id_field: str):
    """Verify that file is owner by user who performs operation or by entity
    which is currently validated."""

    def validator(
        key: FlattenKey,
        data: FlattenDataDict,
        errors: FlattenErrorDict,
        context: Context,
    ) -> None:
        user = authz._get_user(context.get("user"))  # type: ignore
        ignore_auth = context.get("ignore_auth")
        if ignore_auth or (user and user.sysadmin):
            return

        file = context["session"].get(File, data[key])

        if user and file and file.owner_info:
            owner_id = data.get(key[:-1] + (id_field,))
            actual = file.owner_info.owner_type, file.owner_info.owner_id
            if actual in [("user", user.id), (owner_type, owner_id)]:
                return

        errors[key].append("Is not an owner of the file")

    return validator
