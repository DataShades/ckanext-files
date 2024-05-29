from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from werkzeug.utils import secure_filename

import ckan.plugins.toolkit as tk
from ckan import model
from ckan.logic import validate
from ckan.types import Context

from ckanext.files import exceptions, shared
from ckanext.files.model import File, Owner

from . import schema


def _flat_mask(data: dict[str, Any]) -> dict[tuple[Any, ...], Any]:
    result: dict[tuple[Any, ...], Any] = {}

    for k, v in data.items():
        if isinstance(v, dict):
            result.update({(k,) + sk: sv for sk, sv in _flat_mask(v).items()})
        else:
            result[(k,)] = v

    return result


@tk.side_effect_free
@validate(schema.file_search_by_user)
def files_file_search_by_user(
    context: Context,
    data_dict: dict[str, Any],
) -> dict[str, Any]:
    tk.check_access("files_file_search_by_user", context, data_dict)
    sess = context["session"]

    user = model.User.get(data_dict.get("user", context.get("user", "")))
    if not user:
        raise tk.ObjectNotFound("user")

    q = sess.query(File).join(
        Owner,
        sa.and_(File.id == Owner.item_id, Owner.item_type == "file"),
    )

    if "storage" in data_dict:
        q = q.filter(File.storage == data_dict["storage"])

    q = q.filter(sa.and_(Owner.owner_type == "user", Owner.owner_id == user.id))

    inspector: Any = sa.inspect(File)
    columns = inspector.columns

    for mask in ["storage_data", "plugin_data"]:
        if mask in data_dict:
            for k, v in _flat_mask(data_dict[mask]).items():
                field = columns[mask]
                for segment in k:
                    field = field[segment]

                q = q.filter(field.astext == v)

    total = q.count()

    parts = data_dict["sort"].split(".")
    sort = parts[0]
    sort_path = parts[1:]

    if sort not in columns:
        raise tk.ValidationError({"sort": ["Unknown sort column"]})

    column = columns[sort]

    if sort_path and sort == "storage_data":
        for part in sort_path:
            column = column[part]

    if data_dict["reverse"]:
        column = column.desc()

    q = q.order_by(column)

    q = q.limit(data_dict["rows"]).offset(data_dict["start"])

    return {"count": total, "results": [f.dictize(context) for f in q]}


@validate(schema.file_create)
def files_file_create(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    tk.check_access("files_file_create", context, data_dict)
    _ensure_name(data_dict)

    extras = data_dict.get("__extras", {})

    try:
        storage = shared.get_storage(data_dict["storage"])
    except exceptions.UnknownStorageError as err:
        raise tk.ValidationError({"storage": [str(err)]})  # noqa: B904

    if not storage.supports(shared.Capability.CREATE):
        raise tk.ValidationError({"storage": ["Operation is not supported"]})

    filename = secure_filename(data_dict["name"])
    try:
        storage_data = storage.upload(
            filename,
            data_dict["upload"],
            extras,
        )
    except exceptions.UploadError as err:
        raise tk.ValidationError({"upload": [str(err)]})  # noqa: B904

    fileobj = File(
        name=filename,
        storage=data_dict["storage"],
        storage_data=storage_data,
        completed=True,
    )
    context["session"].add(fileobj)

    _add_owner(context, "file", fileobj.id)
    context["session"].commit()

    return fileobj.dictize(context)


def _ensure_name(
    data_dict: dict[str, Any],
    name_field: str = "name",
    upload_field: str = "upload",
):
    if name_field in data_dict:
        return
    name = data_dict[upload_field].filename
    if not name:
        raise tk.ValidationError(
            {
                name_field: [
                    "Name is missing and cannot be deduced from {}".format(
                        upload_field,
                    ),
                ],
            },
        )
    data_dict[name_field] = name


def _add_owner(context: Context, item_type: str, item_id: str):
    user = model.User.get(context.get("user", ""))
    if user:
        owner = Owner(
            item_id=item_id,
            item_type=item_type,
            owner_id=user.id,
            owner_type="user",
            access=Owner.ACCESS_FULL,
        )
        context["session"].add(owner)


def _delete_owners(context: Context, item_type: str, item_id: str):
    stmt = sa.delete(Owner).where(
        sa.and_(
            Owner.item_type == item_type,
            Owner.item_id == item_id,
        ),
    )
    context["session"].execute(stmt)


@validate(schema.file_delete)
def files_file_delete(context: Context, data_dict: dict[str, Any]) -> bool:
    tk.check_access("files_file_delete", context, data_dict)

    data_dict["id"]
    fileobj = context["session"].query(File).filter_by(id=data_dict["id"]).one_or_none()
    if not fileobj:
        raise tk.ObjectNotFound("file")

    storage = shared.get_storage(fileobj.storage)
    if not storage.supports(shared.Capability.REMOVE):
        raise tk.ValidationError({"storage": ["Operation is not supported"]})

    try:
        storage.remove(fileobj.storage_data)
    except exceptions.PermissionError as err:
        raise tk.NotAuthorized(str(err))  # noqa: B904

    _delete_owners(context, "file", fileobj.id)
    context["session"].delete(fileobj)
    context["session"].commit()

    return fileobj.dictize(context)


@tk.side_effect_free
@validate(schema.file_show)
def files_file_show(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    tk.check_access("files_file_show", context, data_dict)

    fileobj = (
        context["session"].query(File).filter(File.id == data_dict["id"]).one_or_none()
    )
    if not fileobj:
        raise tk.ObjectNotFound("file")

    return fileobj.dictize(context)


@validate(schema.file_rename)
def files_file_rename(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    tk.check_access("files_file_rename", context, data_dict)

    fileobj: File | None = (
        context["session"].query(File).filter(File.id == data_dict["id"]).one_or_none()
    )
    if not fileobj:
        raise tk.ObjectNotFound("file")

    fileobj.name = secure_filename(data_dict["name"])
    fileobj.touch()
    context["session"].commit()

    return fileobj.dictize(context)


@validate(schema.upload_initialize)
def files_upload_initialize(
    context: Context,
    data_dict: dict[str, Any],
) -> dict[str, Any]:
    tk.check_access("files_upload_initialize", context, data_dict)
    _ensure_name(data_dict)
    extras = data_dict.get("__extras", {})

    try:
        storage = shared.get_storage(data_dict["storage"])
    except exceptions.UnknownStorageError as err:
        raise tk.ValidationError({"storage": [str(err)]})  # noqa: B904

    if not storage.supports(shared.Capability.MULTIPART_UPLOAD):
        raise tk.ValidationError({"storage": ["Operation is not supported"]})

    filename = secure_filename(data_dict["name"])
    try:
        storage_data = storage.initialize_multipart_upload(
            filename,
            extras,
        )
    except exceptions.UploadError as err:
        raise tk.ValidationError({"upload": [str(err)]})  # noqa: B904

    fileobj = File(
        name=filename,
        storage=data_dict["storage"],
        storage_data=storage_data,
    )
    context["session"].add(fileobj)
    _add_owner(context, "file", fileobj.id)
    context["session"].commit()

    return fileobj.dictize(context)


@tk.side_effect_free
@validate(schema.upload_show)
def files_upload_show(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    tk.check_access("files_upload_show", context, data_dict)
    file_dict = tk.get_action("files_file_show")(context, data_dict)

    if file_dict["completed"]:
        raise tk.ObjectNotFound("upload")

    storage = shared.get_storage(file_dict["storage"])
    storage_data = storage.show_multipart_upload(file_dict["storage_data"])

    return dict(file_dict, storage_data=storage_data)


@validate(schema.upload_update)
def files_upload_update(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    tk.check_access("files_upload_update", context, data_dict)

    extras = data_dict.get("__extras", {})

    fileobj = context["session"].query(File).filter_by(id=data_dict["id"]).one_or_none()
    if not fileobj:
        raise tk.ObjectNotFound("upload")

    storage = shared.get_storage(fileobj.storage)

    try:
        fileobj.storage_data = storage.update_multipart_upload(
            fileobj.storage_data,
            extras,
        )
    except exceptions.UploadError as err:
        raise tk.ValidationError({"upload": [str(err)]})  # noqa: B904

    context["session"].commit()

    return fileobj.dictize(context)


@validate(schema.upload_complete)
def files_upload_complete(
    context: Context,
    data_dict: dict[str, Any],
) -> dict[str, Any]:
    tk.check_access("files_upload_complete", context, data_dict)

    extras = data_dict.get("__extras", {})

    data_dict["id"]
    fileobj = context["session"].query(File).filter_by(id=data_dict["id"]).one_or_none()
    if not fileobj:
        raise tk.ObjectNotFound("upload")

    storage = shared.get_storage(fileobj.storage)

    try:
        fileobj.storage_data = storage.complete_multipart_upload(
            fileobj.storage_data,
            extras,
        )
    except exceptions.UploadError as err:
        raise tk.ValidationError({"upload": [str(err)]})  # noqa: B904

    fileobj.completed = True
    context["session"].commit()

    return fileobj.dictize(context)
