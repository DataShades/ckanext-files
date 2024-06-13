from __future__ import annotations

import logging

import ckan.plugins.toolkit as tk
from ckan import authz
from ckan.types import Context, FlattenDataDict, FlattenErrorDict, FlattenKey

from ckanext.files import utils
from ckanext.files.shared import File, FileData, get_storage

log = logging.getLogger(__name__)


def files_skip_absolute_url(
    key: FlattenKey,
    data: FlattenDataDict,
    errors: FlattenErrorDict,
    context: Context,
):
    """Stop validatio and accept value if it's an absolute URL"""
    value = data[key]
    if isinstance(value, str) and value.startswith(("https://", "http://")):
        raise tk.StopOnError


def files_file_into_public_url(
    key: FlattenKey,
    data: FlattenDataDict,
    errors: FlattenErrorDict,
    context: Context,
):
    """Transform file ID into public URL or raise error if public URL is not
    supported."""
    value: str | list[str] = data[key]
    use_list = isinstance(value, list)
    ids = value if use_list else [value]
    result = []
    for file_id in ids:
        file = context["session"].get(File, file_id)
        if not file:
            msg = "File does not exist"
            errors[key].append(msg)
            raise tk.StopOnError

        info = FileData.from_model(file)
        storage = get_storage(file.storage)
        url = storage.public_link(info)
        if not url:
            msg = "File does not support public URLs"
            errors[key].append(msg)
            raise tk.StopOnError
        result.append(url)

    data[key] = result if use_list else result[0]


def files_into_upload(
    key: FlattenKey,
    data: FlattenDataDict,
    errors: FlattenErrorDict,
    context: Context,
):
    """Convert value into Upload object"""
    try:
        data[key] = utils.make_upload(data[key])

    except TypeError as err:
        msg = f"Unsupported source type: {err}"
        errors[key].append(msg)
        raise tk.StopOnError from err

    except ValueError as err:
        msg = f"Wrong file: {err}"
        errors[key].append(msg)
        raise tk.StopOnError from err


def files_parse_filesize(
    key: FlattenKey,
    data: FlattenDataDict,
    errors: FlattenErrorDict,
    context: Context,
):
    """Convert human-readable filesize into an integer."""
    value = data[key]
    if isinstance(value, int):
        return

    try:
        data[key] = utils.parse_filesize(value)
    except ValueError as err:
        msg = f"Wrong filesize string: {value}"
        errors[key].append(msg)
        raise tk.StopOnError from err


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
        errors[key].append(msg)
        raise tk.StopOnError

    return validator


def files_file_id_exists(
    key: FlattenKey,
    data: FlattenDataDict,
    errors: FlattenErrorDict,
    context: Context,
):
    """Verify that file ID exists."""
    value: str | list[str] = data[key]
    ids = value if isinstance(value, list) else [value]

    for file_id in ids:
        file = context["session"].get(File, file_id)
        if not file:
            msg = "File does not exist"
            errors[key].append(msg)
            raise tk.StopOnError


def files_file_content_type(*supported_types: str):
    """Verify that file ID exists."""

    def validator(
        key: FlattenKey,
        data: FlattenDataDict,
        errors: FlattenErrorDict,
        context: Context,
    ):
        value: str | list[str] = data[key]

        ids = value if isinstance(value, list) else [value]

        for file_id in ids:
            file = context["session"].get(File, file_id)
            if not file:
                msg = "File does not exist"
                errors[key].append(msg)
                raise tk.StopOnError

            actual = file.content_type

            if not utils.is_supported_type(actual, supported_types):
                expected = ", ".join(supported_types)
                msg = (
                    f"Type {actual} is not supported."
                    + f" Use one of the following types: {expected}"
                )
                errors[key].append(msg)
                raise tk.StopOnError

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
        msg = "Is not an owner of the file"

        value = data[key]
        ids: list[str] = value if isinstance(value, list) else [value]

        user = authz._get_user(context.get("user"))  # type: ignore

        for file_id in ids:
            file = context["session"].get(File, file_id)

            if not file or not file.owner_info:
                errors[key].append(msg)
                raise tk.StopOnError

            id_field_path = key[:-1] + (id_field,)
            owner_id = data.get(id_field_path)
            actual = file.owner_info.owner_type, file.owner_info.owner_id

            if actual == (owner_type, owner_id):
                continue

            if not user or actual != ("user", user.id):
                errors[key].append(msg)
                continue

            if file.owner_info.pinned:
                errors[key].append("File is pinned")
                continue

            utils.OwnershipTransferRequest.create(file_id, owner_type, id_field_path)

    return validator
