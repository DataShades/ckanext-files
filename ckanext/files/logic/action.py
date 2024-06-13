from __future__ import annotations

from typing import Any, cast

import sqlalchemy as sa
from werkzeug.utils import secure_filename

import ckan.plugins.toolkit as tk
from ckan import model
from ckan.logic import validate
from ckan.types import Action, Context

from ckanext.files import exceptions, shared, utils
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
def files_file_search_by_user(  # noqa: C901
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
def files_file_search(  # noqa: C901, PLR0912
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

    for field in ["owner_type", "owner_id", "pinned"]:
        if field in data_dict:
            stmt = stmt.where(getattr(Owner, field) == data_dict[field])

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

        if (
            isinstance(v, list)
            and len(v) == 2  # noqa: PLR2004
            and v[0] in ["=", "<", ">", "!=", "like"]
        ):
            op, v = cast("list[Any]", v)  # noqa: PLW2901
        else:
            op = "="

        column_type = columns[k].type.python_type
        if not isinstance(v, column_type) and v is not None:
            v = str(v)  # noqa: PLW2901

        if v is None:
            if op == "=":
                op = "is"
            elif op == "!=":
                op = "is not"

        stmt = stmt.where(columns[k].bool_op(op)(v))

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

    _set_user_owner(context, "file", fileobj.id)
    context["session"].commit()

    return fileobj.dictize(context)


def _set_user_owner(context: Context, item_type: str, item_id: str):
    user = model.User.get(context.get("user", ""))
    if user:
        owner = Owner(
            item_id=item_id,
            item_type=item_type,
            owner_id=user.id,
            owner_type="user",
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

    fileobj = context["session"].get(
        File if data_dict["completed"] else Multipart,
        data_dict["id"],
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

    fileobj = context["session"].get(
        File if data_dict["completed"] else Multipart,
        data_dict["id"],
    )
    if not fileobj:
        raise tk.ObjectNotFound("file")

    return fileobj.dictize(context)


@validate(schema.file_rename)
def files_file_rename(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    tk.check_access("files_file_rename", context, data_dict)

    fileobj = context["session"].get(
        File if data_dict["completed"] else Multipart,
        data_dict["id"],
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
    _set_user_owner(context, "multipart", fileobj.id)
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

    fileobj = context["session"].get(Multipart, data_dict["id"])
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
    multipart = context["session"].get(Multipart, data_dict["id"])
    if not multipart:
        raise tk.ObjectNotFound("upload")

    storage = shared.get_storage(multipart.storage)

    fileobj = File(
        name=multipart.name,
        storage=multipart.storage,
    )

    try:
        storage.multipart_complete(
            shared.MultipartData.from_model(multipart),
            **extras,
        ).into_model(fileobj)
    except exceptions.UploadError as err:
        raise tk.ValidationError({"upload": [str(err)]}) from err

    sess.query(Owner).where(
        Owner.item_type == "multipart",
        Owner.item_id == multipart.id,
    ).update({"item_id": fileobj.id, "item_type": "file"})
    sess.add(fileobj)
    sess.delete(multipart)
    sess.commit()

    return fileobj.dictize(context)


@validate(schema.transfer_ownership)
def files_transfer_ownership(
    context: Context,
    data_dict: dict[str, Any],
) -> dict[str, Any]:
    tk.check_access("files_transfer_ownership", context, data_dict)
    sess = context["session"]
    fileobj = context["session"].get(
        File if data_dict["completed"] else Multipart,
        data_dict["id"],
    )
    if not fileobj:
        raise tk.ObjectNotFound("file")

    owner = fileobj.owner_info
    if not owner:
        owner = Owner(
            item_id=fileobj.id,
            item_type="file" if data_dict["completed"] else "multipart",
        )
        context["session"].add(owner)

    if owner.pinned and not data_dict["force"]:
        raise tk.ValidationError(
            {
                "force": ["Must be enabled to transfer pinned files"],
            },
        )
    owner.owner_id = data_dict["owner_id"]
    owner.owner_type = data_dict["owner_type"]
    owner.pinned = data_dict["pin"]
    sess.commit()

    return fileobj.dictize(context)


@validate(schema.file_pin)
def files_file_pin(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    tk.check_access("files_file_pin", context, data_dict)
    sess = context["session"]
    fileobj = context["session"].get(
        File if data_dict["completed"] else Multipart,
        data_dict["id"],
    )
    if not fileobj:
        raise tk.ObjectNotFound("file")

    owner = fileobj.owner_info
    if not owner:
        raise tk.ValidationError({"id": ["File has no owner"]})

    owner.pinned = True
    sess.commit()

    return fileobj.dictize(context)


@validate(schema.file_unpin)
def files_file_unpin(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    tk.check_access("files_file_unpin", context, data_dict)
    sess = context["session"]
    fileobj = context["session"].get(
        File if data_dict["completed"] else Multipart,
        data_dict["id"],
    )
    if not fileobj:
        raise tk.ObjectNotFound("file")

    owner = fileobj.owner_info
    if not owner:
        raise tk.ValidationError({"id": ["File has no owner"]})

    owner.pinned = False
    sess.commit()

    return fileobj.dictize(context)


@tk.chained_action
def _chained_action(
    next_action: Action,
    context: Context,
    data_dict: dict[str, Any],
) -> Any:
    return next_action(context, data_dict)


package_create = utils.action_with_ownership_transfer(_chained_action, "package_create")
package_update = utils.action_with_ownership_transfer(_chained_action, "package_update")
resource_create = utils.action_with_ownership_transfer(
    _chained_action,
    "resource_create",
)
resource_update = utils.action_with_ownership_transfer(
    _chained_action,
    "resource_update",
)
group_create = utils.action_with_ownership_transfer(_chained_action, "group_create")
group_update = utils.action_with_ownership_transfer(_chained_action, "group_update")
organization_create = utils.action_with_ownership_transfer(
    _chained_action,
    "organization_create",
)
organization_update = utils.action_with_ownership_transfer(
    _chained_action,
    "organization_update",
)
user_create = utils.action_with_ownership_transfer(_chained_action, "user_create")
user_update = utils.action_with_ownership_transfer(_chained_action, "user_update")
