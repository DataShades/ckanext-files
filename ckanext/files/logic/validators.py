from __future__ import annotations

import logging
from typing import Any, Literal

import ckan.plugins.toolkit as tk
from ckan import authz
from ckan.types import Context, FlattenDataDict, FlattenErrorDict, FlattenKey

from ckanext.files import exceptions, shared, task, utils
from ckanext.files.shared import File, FileData, get_storage

log = logging.getLogger(__name__)


# unstable
def files_skip_absolute_url(value: Any):
    """Stop validation and accept value if it's an absolute URL."""
    if isinstance(value, str) and value.startswith(("https://", "http://")):
        raise tk.StopOnError


# unstable
def files_verify_url_type_and_value(
    key: FlattenKey,
    data: FlattenDataDict,
    errors: FlattenErrorDict,
    context: Context,
):
    """Skip validation for non-file resources.

    Remove everything before last `/` for file resources.
    """
    if data.get(key[:-1] + ("url_type",)) != "file":
        raise tk.StopOnError

    value = data[key]
    if value:
        data[key] = value.rsplit("/", 1)[-1]


# unstable
def files_id_into_resource_download_url(
    key: FlattenKey,
    data: FlattenDataDict,
    errors: FlattenErrorDict,
    context: Context,
):
    """Transform file ID into resource's download URL."""
    package_id = data.get(key[:-1] + ("package_id",))
    resource_id = data.get(key[:-1] + ("id",))

    data[key] = tk.url_for(
        "files.resource_download",
        id=package_id,
        resource_id=resource_id,
        filename=data[key],
        _external=True,
    )


# unstable
def files_file_into_public_url(
    key: FlattenKey,
    data: FlattenDataDict,
    errors: FlattenErrorDict,
    context: Context,
):
    """Transform ID into public URL or raise error if not supported."""
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
    """Convert value into Upload object."""
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
    ):
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
    value = data[key]
    use_list = isinstance(value, list)
    ids: str | list[str] = value if use_list else [value]

    for file_id in ids:
        file = context["session"].get(File, file_id)
        if not file:
            msg = "File does not exist"
            errors[key].append(msg)
            raise tk.StopOnError


# unstable
def files_content_type_from_file(file_field: str, if_empty: bool = False):
    """Copy MIMEtype of the file in specified field."""

    def validator(
        key: FlattenKey,
        data: FlattenDataDict,
        errors: FlattenErrorDict,
        context: Context,
    ):
        value = data[key]
        if value and if_empty:
            return

        file_id = data.get(key[:-1] + (file_field,))
        if not file_id:
            return
        file_id = file_id.rsplit("/", 1)[-1]
        file = context["session"].get(File, file_id)

        if file:
            data[key] = file.content_type

    return validator


def files_accept_file_with_type(*supported_types: str):
    """Verify that file has allowed MIMEtype."""

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


def files_accept_file_with_storage(*supported_storages: str):
    """Verify that file stored inside specified storage."""

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

            if file.storage not in supported_storages:
                expected = ", ".join(supported_storages)
                msg = (
                    f"Storage {file.storage} is not supported."
                    + f" Use one of the following storages: {expected}"
                )
                errors[key].append(msg)
                raise tk.StopOnError

    return validator


def files_transfer_ownership(owner_type: str, id_field: str = "id"):
    """Tranfer file ownership to validated object."""

    def validator(
        key: FlattenKey,
        data: FlattenDataDict,
        errors: FlattenErrorDict,
        context: Context,
    ):
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

            shared.add_task(
                task.OwnershipTransferTask(file_id, owner_type, id_field_path),
            )

    return validator


# unstable
def files_validate_with_storage(storage_name: str):
    """Apply storage validators to file."""
    storage = shared.get_storage(storage_name)

    def validator(value: shared.Upload):
        try:
            storage.validate(value)
        except exceptions.UploadError as err:
            raise tk.Invalid(str(err)) from err
        return value

    return validator


# unstable
def files_upload_as(  # noqa: PLR0913
    storage: str,
    owner_type: str,
    id_field: str,
    attach_as: Literal["id", "public_url"] | None,
    using_action: str | None = None,
    destination_field: str | None = None,
):
    """This validator exists for backward compatibility and will be removed.

    Schedule file upload after success of the action. File will be attached as
    ID/public URL to owner.

    """

    def validator(
        key: FlattenKey,
        data: FlattenDataDict,
        errors: FlattenErrorDict,
        context: Context,
    ):
        value: utils.Upload = data.pop(key)
        id_field_path = key[:-1] + (id_field,)
        shared.add_task(
            task.UploadAndAttachTask(
                storage,
                value,
                owner_type,
                id_field_path,
                attach_as,
                using_action,
                destination_field,
            ),
        )

    return validator
