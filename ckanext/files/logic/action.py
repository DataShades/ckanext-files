from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy.exc import ProgrammingError
from werkzeug.utils import secure_filename

import ckan.plugins.toolkit as tk
from ckan import model
from ckan.logic import validate
from ckan.types import Action, Context

from ckanext.files import shared, utils
from ckanext.files.shared import File, Owner, TransferHistory

from . import schema

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement
    from sqlalchemy.sql.schema import Column
log = logging.getLogger(__name__)


@tk.chained_action
def _chained_action(
    next_action: Action,
    context: Context,
    data_dict: dict[str, Any],
) -> Any:
    return next_action(context, data_dict)


package_create = shared.with_task_queue(_chained_action, "package_create")
package_update = shared.with_task_queue(_chained_action, "package_update")
resource_create = shared.with_task_queue(
    _chained_action,
    "resource_create",
)
resource_update = shared.with_task_queue(
    _chained_action,
    "resource_update",
)
group_create = shared.with_task_queue(_chained_action, "group_create")
group_update = shared.with_task_queue(_chained_action, "group_update")
organization_create = shared.with_task_queue(
    _chained_action,
    "organization_create",
)
organization_update = shared.with_task_queue(
    _chained_action,
    "organization_update",
)
user_create = shared.with_task_queue(_chained_action, "user_create")
user_update = shared.with_task_queue(_chained_action, "user_update")


def _set_user_owner(context: Context, item_type: str, item_id: str):
    """Add user from context as file owner."""
    user = model.User.get(context.get("user", ""))
    if user:
        owner = Owner(
            item_id=item_id,
            item_type=item_type,
            owner_id=user.id,
            owner_type="user",
        )
        context["session"].add(owner)


def _process_filters(  # noqa: C901
    filters: dict[str, Any], columns: Mapping[str, Column[Any]]
) -> ColumnElement[bool]:
    """Transform `{"$and":[{"field":{"$eq":"value"}}]}` filters into SQL filters."""
    items = []

    for k, v in filters.items():
        if k in ["$and", "$or"]:
            if not isinstance(v, list):
                raise tk.ValidationError({"filters": [f"Only lists are allowed inside {k}"]})
            nested_items = [
                _process_filters(sub_filters, columns)
                for sub_filters in v  # pyright: ignore[reportUnknownVariableType]
                if isinstance(sub_filters, dict)
            ]
            if len(nested_items) > 1:
                wrapper = sa.and_ if k == "$and" else sa.or_
                items.append(wrapper(*nested_items).self_group())
            else:
                items.extend(nested_items)

        elif k in ["storage_data", "plugin_data"]:
            items.extend(_process_data(columns[k], v))

        elif k in columns:
            items.extend(_process_field(columns[k], v))

        else:
            raise tk.ValidationError({"filters": [f"Unknown filter: {k}"]})

    if len(items) == 1:
        return items[0]  # pyright: ignore[reportUnknownVariableType]

    return sa.and_(*items).self_group()


_op_map = {
    "$eq": "=",
    "$ne": "!=",
    "$lt": "<",
    "$lte": "<=",
    "$gt": ">",
    "$gte": ">=",
    "$in": "IN",
    "$is": "IS",
    "$isnot": "IS NOT",
    "$like": "LIKE",
    "$ilike": "ILIKE",
}


def _process_field(col: Column[Any], value: Any):  # noqa: C901
    """Transform `{"field":{"$eq":"value"}}` into SQL filters."""
    if isinstance(value, list):
        value = {"$in": value}  # pyright: ignore[reportUnknownVariableType]

    elif value is None:
        value = {"$eq": None}

    elif not isinstance(value, dict):
        value = {"$eq": value}

    for operator, filter in value.items():  # pyright: ignore[reportUnknownVariableType]
        column = col
        if operator not in _op_map:
            raise tk.ValidationError({"filters": [f"Operator {operator} is not supported"]})
        op = _op_map[operator]
        if filter is None:
            if op == "=":
                op = "is"
            elif op == "!=":
                op = "IS NOT"

        elif operator == "$in" and isinstance(filter, list):
            filter = tuple(filter)  # pyright: ignore[reportUnknownVariableType]  # noqa: PLW2901
        elif not isinstance(filter, col.type.python_type):
            filter = str(filter)  # noqa: PLW2901
            column = sa.func.cast(column, sa.Text)

        func = column.bool_op(op)
        yield func(filter)


def _process_data(col: ColumnElement[Any], value: Any):  # pyright: ignore[reportUnknownParameterType]
    """Transform file/plugin data filters into SQL JSONB filters."""
    if not isinstance(value, dict):
        value = {"$eq": value}

    for k, v in value.items():  # pyright: ignore[reportUnknownVariableType]
        if k in _op_map:
            op = _op_map[k]
            if v is None:
                if op == "=":
                    op = "is"
                elif op == "!=":
                    op = "IS NOT"

            if isinstance(v, bool):
                col = sa.cast(col, sa.Boolean)

            elif isinstance(v, int):
                col = sa.cast(col, sa.Integer)

            elif isinstance(v, float):
                col = sa.cast(col, sa.Float)

            else:
                col = col.astext

            yield col.bool_op(op)(v)

        else:
            yield from _process_data(col[k], v)


def _process_sort(
    sort: str | list[str] | list[list[str]] | Any,
    columns: Mapping[str, Column[Any]],
):
    """Transform sort field into SQL ordering statements."""
    if isinstance(sort, str):
        sort = [sort]

    for part in sort:
        if isinstance(part, str):
            field: str = part
            direction = "asc"

        elif isinstance(part, list) and len(part) == 2:  # noqa: PLR2004
            field, direction = part  # pyright: ignore[reportUnknownVariableType]

        else:
            raise tk.ValidationError({"sort": [f"Invalid sort value: {part}"]})

        if direction not in ["asc", "desc"]:
            raise tk.ValidationError({"sort": [f"Invalid sort direction: {direction}"]})

        if field not in columns:
            raise tk.ValidationError({"sort": [f"Invalid sort field: {field}"]})

        yield getattr(columns[field], direction)()


@tk.side_effect_free
@validate(schema.file_search)
def files_file_search(  # noqa: C901, PLR0912, PLR0915
    context: Context,
    data_dict: dict[str, Any],
) -> dict[str, Any]:
    """Search files.

    /// warning
    This action is not stabilized yet and will change in future.
    ///

    Provides an ability to search files according to [the future CKAN's search
    spec](https://github.com/ckan/ckan/discussions/8444).

    All columns of File model can be used as filters. Before the search, type
    of column and type of filter value are compared. If they are the same,
    original values are used in search. If type different, column value and
    filter value are casted to string.

    This request produces `size = 10` SQL expression:

    ```sh
    $ ckanapi action file_search filters:'{"size": 10}'
    ```

    This request produces `size::text = '10'` SQL expression:

    ```sh
    $ ckanapi action file_search filters:'{"size": "10"}'
    ```

    Even though results are usually not changed, using correct types leads to
    more efficient search.

    Apart from File columns, the following Owner properties can be used for
    searching: `owner_id`, `owner_type`, `pinned`.

    Args:
        start (int): index of first row in result/number of rows to skip. Default: `0`
        rows (int): number of rows to return. Default: `10`
        sort (str): name of File column used for sorting. Default: `name`
        filters (dict[str, Any]): search filters

    Returns:
        dictionary with `count` and `results`
    """
    tk.check_access("files_file_search", context, data_dict)
    sess = context["session"]
    columns = dict(**File.__table__.c, **Owner.__table__.c)

    stmt = (
        sa.select(File)
        .outerjoin(
            Owner,
            sa.and_(File.id == Owner.item_id, Owner.item_type == "file"),
        )
        .where(_process_filters(data_dict["filters"], columns))
    )

    try:
        total: int = sess.scalar(stmt.with_only_columns(sa.func.count()))  # pyright: ignore[reportAssignmentType]
    except ProgrammingError as err:
        sess.rollback()
        msg = "Invalid file search request"
        log.exception(msg)
        raise tk.ValidationError({"filters": [msg]}) from err

    for clause in _process_sort(data_dict["sort"], columns):
        stmt = stmt.order_by(clause)

    stmt = stmt.limit(data_dict["rows"]).offset(data_dict["start"])

    cache = utils.ContextCache(context)
    results: list[shared.File] = [cache.set("file", f.id, f) for f in sess.scalars(stmt)]
    return {"count": total, "results": [f.dictize(context) for f in results]}


@validate(schema.file_create)
def files_file_create(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    """Create a new file.

    This action passes uploaded file to the storage without strict
    validation. File is converted into standard upload object and everything
    else is controlled by storage. The same file may be uploaded to one storage
    and rejected by other, depending on configuration.

    This action is way too powerful to use it directly. The recommended
    approach is to register a different action for handling specific type of
    uploads and call current action internally.

    When uploading a real file(or using `werkqeug.datastructures.FileStorage`),
    name parameter can be omited. In this case, the name of uploaded file is used.

    ```sh
    ckanapi action files_file_create upload@path/to/file.txt
    ```

    When uploading a raw content of the file using string or bytes object, name
    is mandatory.

    ```sh
    ckanapi action files_file_create upload@<(echo -n "hello world") name=file.txt
    ```

    Requires storage with `CREATE` capability.

    Args:
        name (str, optional): human-readable name of the file.
            Default: guess using upload field
        storage (str, optional): name of the storage that will handle the upload.
            Default: `default`
        upload (Uploadable): content of the file as bytes,
            file descriptor or uploaded file

    Returns:
        dictionary with file details.
    """
    tk.check_access("files_file_create", context, data_dict)
    extras = data_dict.get("__extras", {})

    try:
        storage = shared.get_storage(data_dict["storage"])
    except shared.exc.UnknownStorageError as err:
        raise tk.ValidationError({"storage": [str(err)]}) from err

    if not storage.supports(shared.Capability.CREATE):
        raise tk.ValidationError({"storage": ["Operation is not supported"]})

    if "name" not in data_dict:
        filename = data_dict["upload"].filename
        if not filename:
            msg = "Name is missing and cannot be deduced from upload"
            raise tk.ValidationError({"upload": [msg]})
        data_dict["name"] = filename

    filename = secure_filename(data_dict["name"])

    sess = context["session"]
    location = storage.prepare_location(filename, data_dict["upload"])
    stmt = shared.File.by_location(location, data_dict["storage"])
    if fileobj := sess.scalar(stmt):
        raise tk.ValidationError({"upload": ["File already exists"]})

    try:
        storage_data = storage.upload(
            location,
            data_dict["upload"],
            **extras,
        )
    except (shared.exc.UploadError, shared.exc.ExistingFileError) as err:
        raise tk.ValidationError({"upload": [str(err)]}) from err

    fileobj = File(
        name=filename,
        storage=data_dict["storage"],
    )
    storage_data.into_object(fileobj)

    sess.add(fileobj)

    _set_user_owner(context, "file", fileobj.id)

    # TODO: add hook to set plugin_data using extras
    if not context.get("defer_commit"):
        sess.commit()

    sess.commit()

    utils.ContextCache(context).set("file", fileobj.id, fileobj)

    return fileobj.dictize(context)


@validate(schema.file_register)
def files_file_register(context: Context, data_dict: dict[str, Any]):
    """Register untracked file from storage in DB.

    .. note:: Requires storage with `ANALYZE` capability.

    :param location: location of the file in the storage
    :type location: str, optional
    :param storage: name of the storage that will handle the upload.
        Defaults to the configured ``default`` storage.
    :type storage: str, optional

    :returns: file details.

    """
    tk.check_access("files_file_register", context, data_dict)

    try:
        storage = shared.get_storage(data_dict["storage"])
    except shared.exc.UnknownStorageError as err:
        raise tk.ValidationError({"storage": [str(err)]}) from err

    if not storage.supports(shared.Capability.ANALYZE):
        raise tk.ValidationError({"storage": ["Operation is not supported"]})

    sess = context["session"]
    stmt = shared.File.by_location(data_dict["location"], data_dict["storage"])
    if fileobj := sess.scalar(stmt):
        raise tk.ValidationError({"location": ["File is already registered"]})

    try:
        storage_data = storage.analyze(data_dict["location"])
    except shared.exc.MissingFileError as err:
        raise tk.ObjectNotFound("file") from err

    fileobj = shared.File(
        name=secure_filename(storage_data.location),
        storage=data_dict["storage"],
        **storage_data.as_dict(),
    )
    sess.add(fileobj)

    _set_user_owner(context, "file", fileobj.id)

    if not context.get("defer_commit"):
        sess.commit()

    utils.ContextCache(context).set("file", fileobj.id, fileobj)

    return fileobj.dictize(context)


@validate(schema.file_delete)
def files_file_delete(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    """Remove file from storage.

    Unlike packages, file has no `state` field. Removal usually means that file
    details removed from DB and file itself removed from the storage.

    Some storage can implement revisions of the file and keep archived versions
    or backups. Check storage documentation if you need to know whether there
    are chances that file is not completely removed with this operation.

    Requires storage with `REMOVE` capability.

    ```sh
    ckanapi action files_file_delete id=226056e2-6f83-47c5-8bd2-102e2b82ab9a
    ```

    Args:
        id (str): ID of the file

    Returns:
        dictionary with details of the removed file.
    """
    tk.check_access("files_file_delete", context, data_dict)

    cache = utils.ContextCache(context)

    fileobj = cache.get_model("file", data_dict["id"], File)

    if not fileobj:
        raise tk.ObjectNotFound("file")

    storage = shared.get_storage(fileobj.storage)
    if not storage.supports(shared.Capability.REMOVE):
        raise tk.ValidationError({"storage": ["Operation is not supported"]})

    try:
        storage.remove(shared.FileData.from_object(fileobj))
    except shared.exc.PermissionError as err:
        raise tk.NotAuthorized(str(err)) from err

    sess = context["session"]
    sess.delete(fileobj)
    if not context.get("defer_commit"):
        sess.commit()

    sess.commit()

    return fileobj.dictize(context)


@tk.side_effect_free
@validate(schema.file_show)
def files_file_show(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    """Show file details.

    This action only displays information from DB record. There is no way to
    get the content of the file using this action(or any other API action).

    ```sh
    ckanapi action files_file_show id=226056e2-6f83-47c5-8bd2-102e2b82ab9a
    ```

    Args:
        id (str): ID of the file

    Returns:
        dictionary with file details
    """
    tk.check_access("files_file_show", context, data_dict)

    cache = utils.ContextCache(context)
    fileobj = cache.get_model("file", data_dict["id"], File)
    if not fileobj:
        raise tk.ObjectNotFound("file")

    return fileobj.dictize(context)


@validate(schema.file_rename)
def files_file_rename(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    """Rename the file.

    This action changes human-readable name of the file, which is stored in
    DB. Real location of the file in the storage is not modified.

    ```sh
    ckanapi action files_file_show \\
        id=226056e2-6f83-47c5-8bd2-102e2b82ab9a \\
        name=new-name.txt
    ```

    Args:
        id (str): ID of the file
        name (str): new name of the file

    Returns:
        dictionary with file details

    """
    tk.check_access("files_file_rename", context, data_dict)

    cache = utils.ContextCache(context)
    fileobj = cache.get_model(
        "file",
        data_dict["id"],
        File,
    )
    if not fileobj:
        raise tk.ObjectNotFound("file")

    fileobj.name = secure_filename(data_dict["name"])

    if not context.get("defer_commit"):
        context["session"].commit()

    return fileobj.dictize(context)


@tk.side_effect_free
@validate(schema.file_scan)
def files_file_scan(
    context: Context,
    data_dict: dict[str, Any],
) -> dict[str, Any]:
    """List files of the owner.

    This action internally calls files_file_search, but with static values of
    owner filters. If owner is not specified, files filtered by current
    user. If owner is specified, user must pass authorization check to see
    files.

    Args:
        owner_id (str): ID of the owner
        owner_type (str): type of the owner
        **rest (Any): The all other parameters are passed as-is to `files_file_search`.

    Returns:
        dictionary with `count` and `results`
    """
    if not data_dict["owner_id"] and data_dict["owner_type"] == "user":
        user = context.get("auth_user_obj")

        if isinstance(user, model.User) or (user := model.User.get(context["user"])):
            data_dict["owner_id"] = user.id

    tk.check_access("files_file_scan", context, data_dict)

    data_dict["filters"] = {
        "owner_id": data_dict.pop("owner_id"),
        "owner_type": data_dict.pop("owner_type"),
    }
    return tk.get_action("files_file_search")({"ignore_auth": True}, data_dict)


@validate(schema.transfer_ownership)
def files_transfer_ownership(
    context: Context,
    data_dict: dict[str, Any],
) -> dict[str, Any]:
    """Transfer file ownership.

    Args:
        id (str): ID of the file upload
        owner_id (str): ID of the new owner
        owner_type (str): type of the new owner
        force (bool): move file even if it's pinned. Default: `False`
        pin (bool): pin file after transfer to stop future transfers. Default: `False`

    Returns:
        dictionary with details of updated file
    """
    tk.check_access("files_transfer_ownership", context, data_dict)
    sess = context["session"]

    cache = utils.ContextCache(context)

    fileobj = cache.get_model("file", data_dict["id"], File)
    if not fileobj:
        raise tk.ObjectNotFound("file")

    if owner := fileobj.owner:
        if owner.pinned and not data_dict["force"]:
            raise tk.ValidationError(
                {
                    "force": ["Must be enabled to transfer pinned files"],
                },
            )

        if (owner.owner_type, owner.owner_id) != (
            data_dict["owner_type"],
            data_dict["owner_id"],
        ):
            archive = TransferHistory.from_owner(owner, context["user"])
            sess.add(archive)

        owner.owner_id = data_dict["owner_id"]
        owner.owner_type = data_dict["owner_type"]
        owner.pinned = data_dict["pin"]

    else:
        owner = Owner(
            item_id=fileobj.id,
            item_type="file",
            owner_id=data_dict["owner_id"],
            owner_type=data_dict["owner_type"],
        )
        sess.add(owner)

    owner.pinned = data_dict["pin"]

    # without expiration SQLAlchemy fails to synchronize owner value during
    # transfer of unowned files
    sess.expire(fileobj, ["owner"])
    if not context.get("defer_commit"):
        sess.commit()

    return fileobj.dictize(context)


@validate(schema.file_pin)
def files_file_pin(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    """Pin file to the current owner.

    Pinned file cannot be transfered to a different owner. Use it to guarantee
    that file referred by entity is not accidentally transferred to a different
    owner.

    Args:
        id (str): ID of the file

    Returns:
        dictionary with details of updated file
    """
    tk.check_access("files_file_pin", context, data_dict)
    sess = context["session"]

    cache = utils.ContextCache(context)
    fileobj = cache.get_model("file", data_dict["id"], File)
    if not fileobj:
        raise tk.ObjectNotFound("file")

    owner = fileobj.owner
    if not owner:
        raise tk.ValidationError({"id": ["File has no owner"]})

    owner.pinned = True

    if not context.get("defer_commit"):
        sess.commit()

    return fileobj.dictize(context)


@validate(schema.file_unpin)
def files_file_unpin(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    """Pin file to the current owner.

    Pinned file cannot be transfered to a different owner. Use it to guarantee
    that file referred by entity is not accidentally transferred to a different
    owner.

    Args:
        id (str): ID of the file

    Returns:
        dictionary with details of updated file
    """
    tk.check_access("files_file_unpin", context, data_dict)
    sess = context["session"]

    cache = utils.ContextCache(context)
    fileobj = cache.get_model("file", data_dict["id"], File)
    if not fileobj:
        raise tk.ObjectNotFound("file")

    if owner := fileobj.owner:
        owner.pinned = False

    if not context.get("defer_commit"):
        sess.commit()

    return fileobj.dictize(context)


# not included into CKAN ######################################################


@validate(schema.resource_upload)
def files_resource_upload(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    """Create a new file inside resource storage.

    This action internally calls `files_file_create` with `ignore_auth=True`
    and always uses resources storage.

    New file is not attached to resource. You need to call
    `files_transfer_ownership` manually, when resource created. Or you can use
    `files_transfer_ownership("resource","id")` validator to do it
    automatically.

    Args:
        name (str): human-readable name of the file.
            Default: guess using upload field
        upload (Uploadable): content of the file as bytes,
            file descriptor or uploaded file

    Returns:
        dictionary with file details

    """
    tk.check_access("files_resource_upload", context, data_dict)
    storage_name = shared.config.resources_storage()
    if not storage_name:
        raise tk.ValidationError(
            {"upload": ["Resource uploads are not supported"]},
        )

    # TODO: pull cache from the context
    return tk.get_action("files_multipart_start" if data_dict["multipart"] else "files_file_create")(
        Context(context, ignore_auth=True),
        dict(data_dict, storage=storage_name),
    )


@shared.with_task_queue
@validate(schema.file_replace)
def files_file_replace(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    """Replace content of the file.

    New file must have the same MIMEtype as the original file.

    Size and content hash from the new file will replace original values. All
    other fields, including name, remain unchanged.

    ```sh
    ckanapi action files_file_replace id=123 upload@path/to/file.txt
    ```

    Requires storage with `CREATE` and `REMOVE` capability.

    Args:
        id (str): ID of the replaced file
        upload (Uploadable): content of the file as bytes,
            file descriptor or uploaded file

    Returns:
        dictionary with file details.

    """
    tk.check_access("files_file_replace", context, data_dict)

    cache = utils.ContextCache(context)

    fileobj = cache.get_model("file", data_dict["id"], File)
    if not fileobj:
        raise tk.ObjectNotFound("file")

    if fileobj.content_type != data_dict["upload"].content_type:
        raise tk.ValidationError(
            {
                "upload": [
                    "Expected {} but received {}".format(
                        fileobj.content_type,
                        data_dict["upload"].content_type,
                    ),
                ],
            },
        )
    storage = shared.get_storage(fileobj.storage)

    if not storage.supports(shared.Capability.CREATE | shared.Capability.REMOVE):
        raise tk.ValidationError({"storage": ["Operation is not supported"]})

    try:
        storage_data = storage.upload(
            storage.prepare_location(fileobj.name, data_dict["upload"]),
            data_dict["upload"],
        )
    except shared.exc.UploadError as err:
        raise tk.ValidationError({"upload": [str(err)]}) from err

    # with transparent location strategy file will be writted into the same
    # location, so removal may be not required
    if storage_data.location != fileobj.location:
        old_data = shared.FileData.from_object(fileobj)
        shared.add_task(lambda result, idx, prev: storage.remove(old_data))

    storage_data.into_object(fileobj)
    sess = context["session"]
    if not context.get("defer_commit"):
        sess.commit()

    utils.ContextCache(context).set("file", fileobj.id, fileobj)

    return fileobj.dictize(context)


@validate(schema.multipart_start)
def files_multipart_start(
    context: Context,
    data_dict: dict[str, Any],
) -> dict[str, Any]:
    """Initialize multipart(resumable,continuous,signed,etc) upload.

    Apart from standard parameters, different storages can require additional
    data, so always check documentation of the storage before initiating
    multipart upload.

    When upload initialized, storage usually returns details required for
    further upload. It may be a presigned URL for direct upload, or just an ID
    of upload which must be used with `files_multipart_update`.

    Requires storage with `MULTIPART` capability.

    Args:
        storage (str): name of the storage that will handle the upload.
            Default: `default`
        name (str): name of the uploaded file.
        content_type (str): MIMEtype of the uploaded file. Used for validation
        size (oint): Expected size of upload. Used for validation
        hash (str): Expected content hash. If present, used for validation.
        sample (Uploadable|None): optional sample used to override content type

    Returns:
        dictionary with details of initiated upload. Depends on used storage
    """
    tk.check_access("files_multipart_start", context, data_dict)
    extras = data_dict.get("__extras", {})

    try:
        storage = shared.get_storage(data_dict["storage"])
    except shared.exc.UnknownStorageError as err:
        raise tk.ValidationError({"storage": [str(err)]}) from err

    if not storage.supports(shared.Capability.MULTIPART):
        raise tk.ValidationError({"storage": ["Operation is not supported"]})

    filename = secure_filename(data_dict["name"])

    content_type = data_dict["content_type"]

    sample: shared.Upload | None
    if sample := data_dict.get("sample"):
        content_type = sample.content_type

    location = storage.prepare_location(filename, sample)

    try:
        data = storage.multipart_start(
            location,
            data_dict["size"],
            content_type=content_type,
            hash=data_dict["hash"],
            ckan_api=extras,
        )
    except shared.exc.UploadError as err:
        raise tk.ValidationError({"upload": [str(err)]}) from err

    fileobj = File(
        name=filename,
        storage=data_dict["storage"],
    )
    data.into_object(fileobj)

    sess = context["session"]
    sess.add(fileobj)
    _set_user_owner(context, "multipart", fileobj.id)
    sess.commit()

    utils.ContextCache(context).set("file", fileobj.id, fileobj)
    return fileobj.dictize(context)


@validate(schema.multipart_refresh)
def files_multipart_refresh(
    context: Context,
    data_dict: dict[str, Any],
) -> dict[str, Any]:
    """Refresh details of incomplete upload.

    Can be used if upload process was interrupted and client does not know how
    many bytes were already uploaded.

    Requires storage with `MULTIPART` capability.

    Args:
        id (str): ID of the incomplete upload

    Returns:
        dictionary with details of the updated upload

    """
    tk.check_access("files_multipart_refresh", context, data_dict)

    cache = utils.ContextCache(context)
    fileobj = cache.get_model(
        "file",
        data_dict["id"],
        File,
    )
    if not fileobj:
        raise tk.ObjectNotFound("file")

    storage = shared.get_storage(fileobj.storage)
    storage.multipart_refresh(shared.FileData.from_object(fileobj)).into_object(
        fileobj,
    )
    context["session"].commit()

    return fileobj.dictize(context)


@validate(schema.multipart_update)
def files_multipart_update(
    context: Context,
    data_dict: dict[str, Any],
) -> dict[str, Any]:
    """Update incomplete upload.

    Depending on storage this action may require additional parameters. Most
    likely, `upload` with the fragment of uploaded file.

    Requires storage with `MULTIPART` capability.

    Args:
        id (str): ID of the incomplete upload

    Returns:
        dictionary with details of the updated upload

    """
    tk.check_access("files_multipart_update", context, data_dict)

    extras = data_dict.get("__extras", {})

    cache = utils.ContextCache(context)
    fileobj = cache.get_model(
        "file",
        data_dict["id"],
        File,
    )
    if not fileobj:
        raise tk.ObjectNotFound("upload")

    storage = shared.get_storage(fileobj.storage)

    data = shared.FileData.from_object(fileobj)
    try:
        storage.multipart_update(
            data,
            data_dict["upload"],
            data_dict["part"],
            ckan_api=extras,
        ).into_object(fileobj)
    except shared.exc.UploadError as err:
        raise tk.ValidationError({"upload": [str(err)]}) from err

    context["session"].commit()

    return fileobj.dictize(context)


@validate(schema.multipart_complete)
def files_multipart_complete(
    context: Context,
    data_dict: dict[str, Any],
) -> dict[str, Any]:
    """Finalize multipart upload and transform it into completed file.

    Depending on storage this action may require additional parameters. But
    usually it just takes ID and verifies that content type, size and hash
    provided when upload was initialized, match the actual value.

    If data is valid and file is completed inside the storage, new File entry
    with file details created in DB and file can be used just as any normal
    file.

    Requires storage with `MULTIPART` capability.

    Args:
        id (str): ID of the incomplete upload
        keep_storage_data (bool): copy storage data from multipart upload
        keep_plugin_data (bool): copy plugin data from multipart upload

    Returns:
        dictionary with details of the created file

    """
    tk.check_access("files_multipart_complete", context, data_dict)
    sess = context["session"]
    extras = data_dict.get("__extras", {})

    cache = utils.ContextCache(context)
    multipart = cache.get_model("file", data_dict["id"], File)
    if not multipart:
        raise tk.ObjectNotFound("upload")

    storage = shared.get_storage(multipart.storage)

    try:
        storage.multipart_complete(
            shared.FileData.from_object(multipart),
            **extras,
        ).into_object(multipart)
    except shared.exc.UploadError as err:
        raise tk.ValidationError({"upload": [str(err)]}) from err

    sess.commit()

    return multipart.dictize(context)
