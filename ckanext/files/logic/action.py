import sqlalchemy as sa
from werkzeug.utils import secure_filename

import ckan.plugins.toolkit as tk
from ckan import model
from ckan.logic import validate

from ckanext.files import exceptions, shared
from ckanext.files.base import Capability
from ckanext.files.model import File, Owner
from ckanext.files.utils import make_collector

from . import schema

from ckanext.files import types  # isort: skip # noqa: F401


_actions, action = make_collector()


def get_actions():
    return dict(_actions)


def _flat_mask(data):
    # type: (dict[str, types.Any]) -> dict[tuple[types.Any], types.Any]
    result = {}  # type: dict[tuple[types.Any], types.Any]

    for k, v in data.items():
        if isinstance(v, dict):
            result.update({(k,) + sk: sv for sk, sv in _flat_mask(v).items()})
        else:
            result[(k,)] = v

    return result


@action
@tk.side_effect_free
@validate(schema.file_search_by_user)
def files_file_search_by_user(context, data_dict):
    # type: (types.Any, dict[str, types.Any]) -> dict[str, types.Any]
    tk.check_access("files_file_search_by_user", context, data_dict)
    sess = context["session"]

    user = model.User.get(data_dict.get("user", context["user"]))
    if not user:
        raise tk.ObjectNotFound("user")

    q = sess.query(File).join(
        Owner,
        sa.and_(File.id == Owner.item_id, Owner.item_type == "file"),
    )

    if "storage" in data_dict:
        q = q.filter(File.storage == data_dict["storage"])

    q = q.filter(sa.and_(Owner.owner_type == "user", Owner.owner_id == user.id))

    inspector = sa.inspect(File)  # type: types.Any
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


@action
@validate(schema.file_create)
def files_file_create(context, data_dict):
    # type: (types.Any, dict[str, types.Any]) -> dict[str, types.Any]
    tk.check_access("files_file_create", context, data_dict)
    _ensure_name(data_dict)

    extras = data_dict.get("__extras", {})

    try:
        storage = shared.get_storage(data_dict["storage"])
    except exceptions.UnknownStorageError as err:
        raise tk.ValidationError({"storage": [str(err)]})  # noqa: B904

    if not storage.supports(Capability.CREATE):
        raise tk.ValidationError({"storage": ["Operation is not supported"]})

    try:
        storage_data = storage.upload(
            secure_filename(data_dict["name"]),
            data_dict["upload"],
            extras,
        )
    except exceptions.LargeUploadError as err:
        raise tk.ValidationError({"upload": [str(err)]})  # noqa: B904

    fileobj = File(
        name=data_dict["name"],
        storage=data_dict["storage"],
        storage_data=storage_data,
        completed=True,
    )
    context["session"].add(fileobj)
    _set_owner(context, "file", fileobj.id)  # type: ignore
    context["session"].commit()

    return fileobj.dictize(context)


def _ensure_name(data_dict, name_field="name", upload_field="upload"):
    # type: (dict[str, types.Any], str, str) -> None
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


def _set_owner(context, item_type, item_id):
    # type: (types.Any, str, str) -> None
    user = model.User.get(context["user"])
    if user:
        owner = Owner(
            item_id=item_id,
            item_type=item_type,
            owner_id=user.id,
            owner_type="user",
        )
        context["session"].add(owner)


def _delete_owner(context, item_type, item_id):
    # type: (types.Any, str, str) -> None
    stmt = sa.delete(Owner).where(
        sa.and_(
            Owner.item_type == item_type,
            Owner.item_id == item_id,
        ),
    )
    context["session"].execute(stmt)


@action
@validate(schema.file_delete)
def files_file_delete(context, data_dict):
    # type: (types.Any, dict[str, types.Any]) -> bool
    tk.check_access("files_file_delete", context, data_dict)

    data_dict["id"]
    fileobj = context["session"].query(File).filter_by(id=data_dict["id"]).one_or_none()
    if not fileobj:
        raise tk.ObjectNotFound("file")

    storage = shared.get_storage(fileobj.storage)
    if not storage.supports(Capability.REMOVE):
        raise tk.ValidationError({"storage": ["Operation is not supported"]})

    storage.remove(fileobj.storage_data)
    _delete_owner(context, "file", fileobj.id)
    context["session"].delete(fileobj)
    context["session"].commit()

    return fileobj.dictize(context)


@action
@tk.side_effect_free
@validate(schema.file_show)
def files_file_show(context, data_dict):
    # type: (types.Any, dict[str, types.Any]) -> dict[str, types.Any]
    tk.check_access("files_file_show", context, data_dict)

    fileobj = (
        context["session"].query(File).filter(File.id == data_dict["id"]).one_or_none()
    )
    if not fileobj:
        raise tk.ObjectNotFound("file")

    return fileobj.dictize(context)


@action
@validate(schema.file_rename)
def files_file_rename(context, data_dict):
    # type: (types.Any, dict[str, types.Any]) -> dict[str, types.Any]
    tk.check_access("files_file_rename", context, data_dict)

    fileobj = (
        context["session"].query(File).filter(File.id == data_dict["id"]).one_or_none()
    )  # type: File | None
    if not fileobj:
        raise tk.ObjectNotFound("file")

    fileobj.name = data_dict["name"]
    fileobj.touch()
    context["session"].commit()

    return fileobj.dictize(context)


@action
@validate(schema.upload_initialize)
def files_upload_initialize(context, data_dict):
    # type: (types.Any, dict[str, types.Any]) -> dict[str, types.Any]

    tk.check_access("files_upload_initialize", context, data_dict)
    _ensure_name(data_dict)
    extras = data_dict.get("__extras", {})

    try:
        storage = shared.get_storage(data_dict["storage"])
    except exceptions.UnknownStorageError as err:
        raise tk.ValidationError({"storage": [str(err)]})  # noqa: B904

    if not storage.supports(Capability.MULTIPART_UPLOAD):
        raise tk.ValidationError({"storage": ["Operation is not supported"]})

    try:
        storage_data = storage.initialize_multipart_upload(
            secure_filename(data_dict["name"]),
            extras,
        )
    except exceptions.LargeUploadError as err:
        raise tk.ValidationError({"upload": [str(err)]})  # noqa: B904

    fileobj = File(
        name=data_dict["name"],
        storage=data_dict["storage"],
        storage_data=storage_data,
    )
    context["session"].add(fileobj)
    _set_owner(context, "file", fileobj.id)  # type: ignore
    context["session"].commit()

    return fileobj.dictize(context)


@action
@tk.side_effect_free
@validate(schema.upload_show)
def files_upload_show(context, data_dict):
    # type: (types.Any, dict[str, types.Any]) -> dict[str, types.Any]
    tk.check_access("files_upload_show", context, data_dict)
    file_dict = tk.get_action("files_file_show")(context, data_dict)

    if file_dict["completed"]:
        raise tk.ObjectNotFound("upload")

    storage = shared.get_storage(file_dict["storage"])
    storage_data = storage.show_multipart_upload(file_dict["storage_data"])

    return dict(file_dict, storage_data=storage_data)


@action
@validate(schema.upload_update)
def files_upload_update(context, data_dict):
    # type: (types.Any, dict[str, types.Any]) -> dict[str, types.Any]
    tk.check_access("files_upload_update", context, data_dict)

    extras = data_dict.get("__extras", {})

    fileobj = context["session"].query(File).filter_by(id=data_dict["id"]).one_or_none()
    if not fileobj:
        raise tk.ObjectNotFound("upload")

    storage = shared.get_storage(fileobj.storage)

    fileobj.storage_data = storage.update_multipart_upload(fileobj.storage_data, extras)
    context["session"].commit()

    return fileobj.dictize(context)


@action
@validate(schema.upload_complete)
def files_upload_complete(context, data_dict):
    # type: (types.Any, dict[str, types.Any]) -> dict[str, types.Any]
    tk.check_access("files_upload_complete", context, data_dict)

    extras = data_dict.get("__extras", {})

    data_dict["id"]
    fileobj = context["session"].query(File).filter_by(id=data_dict["id"]).one_or_none()
    if not fileobj:
        raise tk.ObjectNotFound("upload")

    storage = shared.get_storage(fileobj.storage)

    fileobj.storage_data = storage.complete_multipart_upload(
        fileobj.storage_data,
        extras,
    )
    fileobj.completed = True
    context["session"].commit()

    return fileobj.dictize(context)
