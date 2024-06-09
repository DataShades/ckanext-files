from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from werkzeug.utils import secure_filename

import ckan.plugins.toolkit as tk
from ckan import model
from ckan.logic import validate
from ckan.types import Context

from ckanext.files import exceptions, shared
from ckanext.files.base import MultipartData
from ckanext.files.model import File, Multipart, Owner

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


@tk.side_effect_free
@validate(schema.file_search)
def files_file_search(
    context: Context,
    data_dict: dict[str, Any],
) -> dict[str, Any]:
    tk.check_access("files_file_search", context, data_dict)
    sess = context["session"]

    if data_dict["completed"]:
        stmt = sa.select(File).outerjoin(
            Owner,
            sa.and_(File.id == Owner.item_id, Owner.item_type == "file"),
        )

        inspector: Any = sa.inspect(File)
    else:
        stmt = sa.select(Multipart).outerjoin(
            Owner,
            sa.and_(Multipart.id == Owner.item_id, Owner.item_type == "multipart"),
        )

        inspector: Any = sa.inspect(Multipart)

    columns = inspector.columns

    for mask in ["storage_data", "plugin_data"]:
        if mask in data_dict:
            for k, v in _flat_mask(data_dict[mask]).items():
                field = columns[mask]
                for segment in k:
                    field = field[segment]

                stmt = stmt.where(field.astext == v)

    for k, v in data_dict.get("__extras", {}).items():
        if k not in columns:
            continue
        if not isinstance(v, columns[k].type.python_type):
            continue

        stmt = stmt.where(columns[k] == v)

    total = sess.scalar(sa.select(sa.func.count()).select_from(stmt))

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

    stmt = stmt.order_by(column)

    stmt = stmt.limit(data_dict["rows"]).offset(data_dict["start"])

    return {"count": total, "results": [f.dictize(context) for f in sess.scalars(stmt)]}


@validate(schema.file_create)
def files_file_create(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    tk.check_access("files_file_create", context, data_dict)
    extras = data_dict.get("__extras", {})

    try:
        storage = shared.get_storage(data_dict["storage"])
    except exceptions.UnknownStorageError as err:
        raise tk.ValidationError({"storage": [str(err)]}) from err

    if not storage.supports(shared.Capability.CREATE):
        raise tk.ValidationError({"storage": ["Operation is not supported"]})

    filename = secure_filename(data_dict["name"])

    try:
        storage_data = storage.upload(
            filename,
            data_dict["upload"],
            **extras,
        )
    except exceptions.UploadError as err:
        raise tk.ValidationError({"upload": [str(err)]}) from err

    fileobj = File(
        name=filename,
        storage=data_dict["storage"],
        storage_data=storage_data,
    )
    storage_data.into_model(fileobj)
    context["session"].add(fileobj)

    _add_owner(context, "file", fileobj.id)
    context["session"].commit()

    return fileobj.dictize(context)


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
def files_file_delete(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    tk.check_access("files_file_delete", context, data_dict)

    fileobj: File | Multipart | None = (
        context["session"]
        .query(File if data_dict["completed"] else Multipart)
        .filter_by(id=data_dict["id"])
        .one_or_none()
    )
    if not fileobj:
        raise tk.ObjectNotFound("file")

    storage = shared.get_storage(fileobj.storage)
    if not storage.supports(shared.Capability.REMOVE):
        raise tk.ValidationError({"storage": ["Operation is not supported"]})

    dc = shared.FileData if data_dict["completed"] else shared.MultipartData
    try:
        storage.remove(dc.from_model(fileobj))
    except exceptions.PermissionError as err:
        raise tk.NotAuthorized(str(err)) from err

    _delete_owners(
        context,
        "file" if data_dict["completed"] else "multipart",
        fileobj.id,
    )
    context["session"].delete(fileobj)
    context["session"].commit()

    return fileobj.dictize(context)


@tk.side_effect_free
@validate(schema.file_show)
def files_file_show(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    tk.check_access("files_file_show", context, data_dict)

    fileobj: File | Multipart | None = (
        context["session"]
        .query(File if data_dict["completed"] else Multipart)
        .filter_by(id=data_dict["id"])
        .one_or_none()
    )
    if not fileobj:
        raise tk.ObjectNotFound("file")

    return fileobj.dictize(context)


@validate(schema.file_rename)
def files_file_rename(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    tk.check_access("files_file_rename", context, data_dict)

    fileobj: File | Multipart | None = (
        context["session"]
        .query(File if data_dict["completed"] else Multipart)
        .filter_by(id=data_dict["id"])
        .one_or_none()
    )
    if not fileobj:
        raise tk.ObjectNotFound("file")

    fileobj.name = secure_filename(data_dict["name"])

    context["session"].commit()

    return fileobj.dictize(context)


@validate(schema.multipart_start)
def files_multipart_start(
    context: Context,
    data_dict: dict[str, Any],
) -> dict[str, Any]:
    tk.check_access("files_multipart_start", context, data_dict)
    extras = data_dict.get("__extras", {})

    try:
        storage = shared.get_storage(data_dict["storage"])
    except exceptions.UnknownStorageError as err:
        raise tk.ValidationError({"storage": [str(err)]}) from err

    if not storage.supports(shared.Capability.MULTIPART):
        raise tk.ValidationError({"storage": ["Operation is not supported"]})

    filename = secure_filename(data_dict["name"])
    try:
        data = storage.multipart_start(
            filename,
            MultipartData(
                filename,
                data_dict["size"],
                data_dict["content_type"],
                data_dict["hash"],
            ),
            **extras,
        )
    except exceptions.UploadError as err:
        raise tk.ValidationError({"upload": [str(err)]}) from err

    fileobj = Multipart(
        name=filename,
        storage=data_dict["storage"],
    )
    data.into_model(fileobj)

    context["session"].add(fileobj)
    _add_owner(context, "multipart", fileobj.id)
    context["session"].commit()

    return fileobj.dictize(context)


@validate(schema.multipart_refresh)
def files_multipart_refresh(
    context: Context,
    data_dict: dict[str, Any],
) -> dict[str, Any]:
    tk.check_access("files_multipart_refresh", context, data_dict)

    fileobj = context["session"].get(Multipart, data_dict["id"])
    if not fileobj:
        raise tk.ObjectNotFound("file")

    storage = shared.get_storage(fileobj.storage)
    storage.multipart_refresh(MultipartData.from_model(fileobj)).into_model(fileobj)
    context["session"].commit()

    return fileobj.dictize(context)


@validate(schema.multipart_update)
def files_multipart_update(
    context: Context,
    data_dict: dict[str, Any],
) -> dict[str, Any]:
    tk.check_access("files_multipart_update", context, data_dict)

    extras = data_dict.get("__extras", {})

    fileobj: Multipart | None = (
        context["session"].query(Multipart).filter_by(id=data_dict["id"]).one_or_none()
    )
    if not fileobj:
        raise tk.ObjectNotFound("upload")

    storage = shared.get_storage(fileobj.storage)

    try:
        storage.multipart_update(
            shared.MultipartData.from_model(fileobj),
            **extras,
        ).into_model(fileobj)
    except exceptions.UploadError as err:
        raise tk.ValidationError({"upload": [str(err)]}) from err

    context["session"].commit()

    return fileobj.dictize(context)


@validate(schema.multipart_complete)
def files_multipart_complete(
    context: Context,
    data_dict: dict[str, Any],
) -> dict[str, Any]:
    tk.check_access("files_multipart_complete", context, data_dict)
    sess = context["session"]
    extras = data_dict.get("__extras", {})

    data_dict["id"]
    fileobj = (
        context["session"].query(Multipart).filter_by(id=data_dict["id"]).one_or_none()
    )
    if not fileobj:
        raise tk.ObjectNotFound("upload")

    storage = shared.get_storage(fileobj.storage)

    result = File(
        name=fileobj.name,
        storage=fileobj.storage,
    )

    try:
        storage.multipart_complete(
            shared.MultipartData.from_model(fileobj),
            **extras,
        ).into_model(result)
    except exceptions.UploadError as err:
        raise tk.ValidationError({"upload": [str(err)]}) from err

    sess.query(Owner).where(
        Owner.item_type == "multipart",
        Owner.item_id == fileobj.id,
    ).update({"item_id": result.id, "item_type": "file"})
    sess.add(result)
    sess.delete(fileobj)
    sess.commit()

    return result.dictize(context)
