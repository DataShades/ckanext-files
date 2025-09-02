from __future__ import annotations

import logging
from typing import Any, Literal, cast

import file_keeper as fk

import ckan.plugins.toolkit as tk
from ckan import authz
from ckan.types import Context, FlattenDataDict, FlattenErrorDict, FlattenKey

from ckanext.files import shared, task, utils

log = logging.getLogger(__name__)


def files_cascade_options(value: Any) -> dict[str, set[str]]:
    if isinstance(value, str):
        value = value.split()

    if isinstance(value, list):
        cascade: dict[str, set[str]] = {}
        for item in cast("list[str]", value):
            type, *rest = item.split(":", 1)
            cascade.setdefault(type, set()).update(rest)
        value = cascade

    if isinstance(value, dict):
        return cast("dict[str, set[str]]", value)

    msg = "Cascade rules are not correct"
    raise tk.Invalid(msg)


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
    sess = context["session"]
    for file_id in ids:
        file = sess.get(shared.File, file_id)
        if not file:
            msg = "File does not exist"
            errors[key].append(msg)
            raise tk.StopOnError

        info = shared.FileData.from_object(file)
        storage = shared.get_storage(file.storage)
        url = storage.permanent_link(info)
        if not url:
            msg = "File does not support permanent URLs"
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
        data[key] = fk.make_upload(data[key])

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
        data[key] = fk.parse_filesize(value)
    except ValueError as err:
        msg = f"Wrong filesize string: {value}"
        errors[key].append(msg)
        raise tk.StopOnError from err


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

    sess = context["session"]
    for file_id in ids:
        file = sess.get(shared.File, file_id)
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
        sess = context["session"]
        file = sess.get(shared.File, file_id)

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
        sess = context["session"]
        for file_id in ids:
            file = sess.get(shared.File, file_id)
            if not file:
                msg = "File does not exist"
                errors[key].append(msg)
                raise tk.StopOnError

            actual = file.content_type

            if not utils.is_supported_type(actual, supported_types):
                expected = ", ".join(supported_types)
                msg = f"Type {actual} is not supported." + f" Use one of the following types: {expected}"
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
        sess = context["session"]

        for file_id in ids:
            file = sess.get(shared.File, file_id)
            if not file:
                msg = "File does not exist"
                errors[key].append(msg)
                raise tk.StopOnError

            if file.storage not in supported_storages:
                expected = ", ".join(supported_storages)
                msg = f"Storage {file.storage} is not supported." + f" Use one of the following storages: {expected}"
                errors[key].append(msg)
                raise tk.StopOnError

    return validator


def files_transfer_ownership(owner_type: str, id_field: str | list[str] = "id"):  # noqa: C901
    """Tranfer file ownership to validated object."""
    if isinstance(id_field, str):
        id_field = [id_field]

    def validator(  # noqa: C901
        key: FlattenKey,
        data: FlattenDataDict,
        errors: FlattenErrorDict,
        context: Context,
    ):
        msg = "Is not an owner of the file"

        value = data[key]
        id_field_path = key[:-1]
        for step in id_field:
            id_field_path = id_field_path[:-1] if step == ".." else id_field_path + (step,)

        if data.get(id_field_path):
            strategy = "value"
            task_destination = data[id_field_path]

        elif len(key) == 1:
            strategy = "path"
            task_destination = id_field_path

        else:
            max_idx = 0
            idx_position = len(key) - 2
            for flat_field in data:
                if flat_field[:idx_position] != key[:idx_position]:
                    continue
                max_idx = max(key[idx_position], flat_field[idx_position])
            strategy = "path"
            task_destination = key[:-2] + (key[-2] - max_idx - 1,)
            for step in id_field:
                task_destination = task_destination[:-1] if step == ".." else task_destination + (step,)

        ids: list[str] = value if isinstance(value, list) else [value]
        user = authz._get_user(context.get("user"))  # pyright: ignore[reportPrivateUsage]
        sess = context["session"]

        for file_id in ids:
            file = sess.get(shared.File, file_id)
            if not file or not file.owner:
                errors[key].append(msg)
                raise tk.StopOnError

            owner_id = data.get(id_field_path)
            actual = file.owner.owner_type, file.owner.owner_id

            if actual == (owner_type, owner_id):
                continue

            if not user or actual != ("user", user.id):
                errors[key].append(msg)
                continue

            if file.owner.pinned:
                errors[key].append("File is pinned")
                continue

            shared.add_task(
                task.OwnershipTransferTask(file_id, owner_type, task_destination, strategy),
            )

    return validator


# unstable
def files_update_resource_url(
    key: FlattenKey,
    data: FlattenDataDict,
    errors: FlattenErrorDict,
    context: Context,
):
    """Transform file ID into resource's download URL."""
    data[key[:-1] + ("url",)] = tk.url_for(
        "files.dispatch_download",
        file_id=data[key],
        _external=True,
    )


# unstable
def files_set_field(field: str, value: Any):
    """Change value of the field to specified value."""

    def validator(
        key: FlattenKey,
        data: FlattenDataDict,
        errors: FlattenErrorDict,
        context: Context,
    ):
        data[key[:-1] + (field,)] = value

    return validator


# unstable
def files_copy_attribute(attribute: str, destination: str):
    """Copy file's attribute into a different field."""

    def validator(
        key: FlattenKey,
        data: FlattenDataDict,
        errors: FlattenErrorDict,
        context: Context,
    ):
        value = data[key]
        sess = context["session"]

        file = sess.get(shared.File, value)
        if not file or not hasattr(file, attribute):
            return

        data[key[:-1] + (destination,)] = getattr(file, attribute)

    return validator


# unstable
def files_validate_with_storage(storage_name: str):
    """Apply storage validators to file."""
    storage = shared.get_storage(storage_name)

    def validator(value: shared.Upload):
        if isinstance(storage, shared.Storage):
            try:
                storage.validate_content_type(value.content_type)
                storage.validate_size(value.size)
            except shared.exc.UploadError as err:
                raise tk.Invalid(str(err)) from err
        return value

    return validator


# unstable
def files_upload_as(  # noqa: PLR0913
    storage: str,
    owner_type: str,
    id_field: str,
    attach_as: Literal["id", "permanent_url"] | None,
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
        value: fk.Upload = data.pop(key)
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
