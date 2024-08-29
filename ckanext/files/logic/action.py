from __future__ import annotations

import copy

from typing import Any, cast

import sqlalchemy as sa
from werkzeug.utils import secure_filename

import ckan.plugins.toolkit as tk
from ckan import model
from ckan.logic import validate
from ckan.types import Action, Context

from ckanext.files import shared, utils
from ckanext.files.shared import File, Multipart, Owner, TransferHistory

from . import schema


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


def _flat_mask(data: dict[str, Any]) -> dict[tuple[Any, ...], Any]:
    result: dict[tuple[Any, ...], Any] = {}

    for k, v in data.items():
        if isinstance(v, dict):
            result.update({(k,) + sk: sv for sk, sv in _flat_mask(v).items()})
        else:
            result[(k,)] = v

    return result


@tk.side_effect_free
@validate(schema.file_search)
def files_file_search(  # noqa: C901, PLR0912, PLR0915
    context: Context,
    data_dict: dict[str, Any],
) -> dict[str, Any]:
    """Search files.

    This action is not stabilized yet and will change in future.

    Provides an ability to search files using exact filter by name,
    content_type, size, owner, etc. Results are paginated and returned in
    package_search manner, as dict with `count` and `results` items.

    All columns of File model can be used as filters. Before the search, type
    of column and type of filter value are compared. If they are the same,
    original values are used in search. If type different, column value and
    filter value are casted to string.

    This request produces `size = 10` SQL expression:
    ```sh
    ckanapi action files_file_search size:10
    ```

    This request produces `size::text = '10'` SQL expression:
    ```sh
    ckanapi action files_file_search size=10
    ```

    Even though results are usually not changed, using correct types leads to
    more efficient search.

    Apart from File columns, the following Owner properties can be used for
    searching: `owner_id`, `owner_type`, `pinned`.

    `storage_data` and `plugin_data` are dictionaries. Filter's value for these
    fields used as a mask. For example, `storage_data={"a": {"b": 1}}` matches
    any File with `storage_data` *containing* item `a` with value that contains
    `b=1`. This works only with data represented by nested dictionaries,
    without other structures, like list or sets.

    Experimental feature: File columns can be passed as a pair of operator and
    value. This feature will be replaced by strictly defined query language at
    some point:

    ```sh
    ckanapi action files_file_search size:'["<", 100]' content_type:'["like", "text/%"]'
    ```
    Fillowing operators are accepted: `=`, `<`, `>`, `!=`, `like`

    Args:
        start (int): index of first row in result/number of rows to skip. Default: `0`
        rows (int): number of rows to return. Default: `10`
        sort (str): name of File column used for sorting. Default: `name`
        reverse (bool): sort results in descending order. Default: `False`
        storage_data (dict[str, Any]): mask for `storage_data` column. Default: `{}`
        plugin_data (dict[str, Any]): mask for `plugin_data` column. Default: `{}`
        owner_id (str): show only specific owner id if present. Default: `None`
        owner_type (str): show only specific owner type if present. Default: `None`
        pinned (bool): show only pinned/unpinned items if present. Default: `None`
        completed (bool): use `False` to search incomplete uploads. Default: `True`

    Returns:
        dictionary with `count` and `results`
    """
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
            value = data_dict[field]
            if value is not None and not (
                field == "pinned" and isinstance(value, bool)
            ):
                value = str(value)
            stmt = stmt.where(getattr(Owner, field) == value)

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

        col = columns[k]
        column_type = col.type.python_type
        if not isinstance(v, column_type) and v is not None:
            v = str(v)  # noqa: PLW2901
            col = sa.func.cast(col, sa.Text)

        if v is None:
            if op == "=":
                op = "is"
            elif op == "!=":
                op = "is not"

        stmt = stmt.where(col.bool_op(op)(v))

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

    cache = utils.ContextCache(context)
    results: list[File] = [cache.set("file", f.id, f) for f in sess.scalars(stmt)]
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
        upload (shared.types.Uploadable): content of the file as bytes,
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

    filename = secure_filename(data_dict["name"])

    try:
        storage_data = storage.upload(
            filename,
            data_dict["upload"],
            **extras,
        )
    except shared.exc.UploadError as err:
        raise tk.ValidationError({"upload": [str(err)]}) from err

    fileobj = File(
        name=filename,
        storage=data_dict["storage"],
    )
    storage_data.into_model(fileobj)
    context["session"].add(fileobj)

    _set_user_owner(context, "file", fileobj.id)
    context["session"].commit()

    utils.ContextCache(context).set("file", fileobj.id, fileobj)

    return fileobj.dictize(context)


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
        upload (shared.types.Uploadable): content of the file as bytes,
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
        storage_data = storage.upload(fileobj.name, data_dict["upload"])
    except shared.exc.UploadError as err:
        raise tk.ValidationError({"upload": [str(err)]}) from err

    # with transparent location strategy file will be writted into the same
    # location, so removal may be not required
    if storage_data.location != fileobj.location:
        old_data = shared.FileData.from_model(fileobj)
        shared.add_task(lambda result, idx, prev: storage.remove(old_data))

    storage_data.into_model(fileobj)
    context["session"].commit()

    utils.ContextCache(context).set("file", fileobj.id, fileobj)

    return fileobj.dictize(context)


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
        completed (bool): use `False` to remove incomplete uploads. Default: `True`

    Returns:
        dictionary with details of the removed file.
    """
    tk.check_access("files_file_delete", context, data_dict)

    cache = utils.ContextCache(context)

    fileobj = cache.get_model(
        "file", data_dict["id"], File if data_dict["completed"] else Multipart
    )

    if not fileobj:
        raise tk.ObjectNotFound("file")

    storage = shared.get_storage(fileobj.storage)
    if not storage.supports(shared.Capability.REMOVE):
        raise tk.ValidationError({"storage": ["Operation is not supported"]})

    dc = shared.FileData if data_dict["completed"] else shared.MultipartData
    try:
        storage.remove(dc.from_model(fileobj))
    except shared.exc.PermissionError as err:
        raise tk.NotAuthorized(str(err)) from err

    context["session"].delete(fileobj)
    context["session"].commit()

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
        completed (bool): use `False` to show incomplete uploads. Default: `True`

    Returns:
        dictionary with file details
    """
    tk.check_access("files_file_show", context, data_dict)

    cache = utils.ContextCache(context)
    fileobj = cache.get_model(
        "file", data_dict["id"], File if data_dict["completed"] else Multipart
    )
    if not fileobj:
        raise tk.ObjectNotFound("file")

    utils.ContextCache(context).set("file", fileobj.id, fileobj)
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
        completed (bool): use `False` to rename incomplete uploads. Default: `True`

    Returns:
        dictionary with file details

    """
    tk.check_access("files_file_rename", context, data_dict)

    cache = utils.ContextCache(context)
    fileobj = cache.get_model(
        "file",
        data_dict["id"],
        File if data_dict["completed"] else Multipart,
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
    try:
        data = storage.multipart_start(
            filename,
            shared.MultipartData(
                filename,
                data_dict["size"],
                data_dict["content_type"],
                data_dict["hash"],
            ),
            **extras,
        )
    except shared.exc.UploadError as err:
        raise tk.ValidationError({"upload": [str(err)]}) from err

    fileobj = Multipart(
        name=filename,
        storage=data_dict["storage"],
    )
    data.into_model(fileobj)

    context["session"].add(fileobj)
    _set_user_owner(context, "multipart", fileobj.id)
    context["session"].commit()

    utils.ContextCache(context).set("file", fileobj.id, fileobj)
    return fileobj.dictize(context)


@validate(schema.multipart_refresh)
def files_multipart_refresh(
    context: Context,
    data_dict: dict[str, Any],
) -> dict[str, Any]:
    """Refresh details of incomplete upload.

    Can be used if upload process was interrupted and client does not how many
    bytes were already uploaded.

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
        Multipart,
    )
    if not fileobj:
        raise tk.ObjectNotFound("file")

    storage = shared.get_storage(fileobj.storage)
    storage.multipart_refresh(shared.MultipartData.from_model(fileobj)).into_model(
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
        Multipart,
    )
    if not fileobj:
        raise tk.ObjectNotFound("upload")

    storage = shared.get_storage(fileobj.storage)

    try:
        storage.multipart_update(
            shared.MultipartData.from_model(fileobj),
            **extras,
        ).into_model(fileobj)
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
    usually it just takes ID and verify that content type, size and hash
    provided when upload was initialized, much the actual value.

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
    multipart = cache.get_model("file", data_dict["id"], Multipart)
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
    except shared.exc.UploadError as err:
        raise tk.ValidationError({"upload": [str(err)]}) from err

    if data_dict["keep_storage_data"]:
        data: Any = copy.deepcopy(multipart.storage_data)
        data.update(fileobj.storage_data)
        fileobj.storage_data = data

    if data_dict["keep_plugin_data"]:
        data: Any = copy.deepcopy(multipart.plugin_data)
        data.update(fileobj.plugin_data)
        fileobj.plugin_data = data

    sess.query(Owner).where(
        Owner.item_type == "multipart",
        Owner.item_id == multipart.id,
    ).update({"item_id": fileobj.id, "item_type": "file"})
    sess.add(fileobj)
    sess.delete(multipart)
    sess.commit()

    cache.set("file", fileobj.id, fileobj)
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

    params = data_dict.pop("__extras", {})
    params.update(data_dict)

    # TODO: pull cache from search context
    return tk.get_action("files_file_search")({"ignore_auth": True}, params)


@validate(schema.transfer_ownership)
def files_transfer_ownership(
    context: Context,
    data_dict: dict[str, Any],
) -> dict[str, Any]:
    """Transfer file ownership.

    Args:
        id (str): ID of the file upload
        completed (bool): use `False` to transfer incomplete uploads. Default: `True`
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

    fileobj = cache.get_model(
        "file",
        data_dict["id"],
        File if data_dict["completed"] else Multipart,
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

    elif owner.pinned and not data_dict["force"]:
        raise tk.ValidationError(
            {
                "force": ["Must be enabled to transfer pinned files"],
            },
        )
    elif (owner.owner_type, owner.owner_id) != (
        data_dict["owner_type"],
        data_dict["owner_id"],
    ):
        archive = TransferHistory.from_owner(owner)
        archive.actor = context["user"]
        sess.add(archive)

    owner.owner_id = data_dict["owner_id"]
    owner.owner_type = data_dict["owner_type"]
    owner.pinned = data_dict["pin"]
    sess.expire(fileobj)
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
        completed (bool): use `False` to pin incomplete uploads. Default: `True`

    Returns:
        dictionary with details of updated file
    """
    tk.check_access("files_file_pin", context, data_dict)
    sess = context["session"]

    cache = utils.ContextCache(context)
    fileobj = cache.get_model(
        "file",
        data_dict["id"],
        File if data_dict["completed"] else Multipart,
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
    """Pin file to the current owner.

    Pinned file cannot be transfered to a different owner. Use it to guarantee
    that file referred by entity is not accidentally transferred to a different
    owner.

    Args:
        id (str): ID of the file
        completed (bool): use `False` to unpin incomplete uploads. Default: `True`

    Returns:
        dictionary with details of updated file
    """
    tk.check_access("files_file_unpin", context, data_dict)
    sess = context["session"]

    cache = utils.ContextCache(context)
    fileobj = cache.get_model(
        "file",
        data_dict["id"],
        File if data_dict["completed"] else Multipart,
    )
    if not fileobj:
        raise tk.ObjectNotFound("file")

    owner = fileobj.owner_info
    if not owner:
        raise tk.ValidationError({"id": ["File has no owner"]})

    owner.pinned = False
    sess.commit()

    return fileobj.dictize(context)


@validate(schema.resource_upload)
def files_resource_upload(
    context: Context, data_dict: dict[str, Any]
) -> dict[str, Any]:
    """Create a new file inside resource storage.

    This action internally calls `files_file_create` with `ignore_auth=True`
    and always uses resources storage.

    New file is not attached to resource. You need to call
    `files_transfer_ownership` manually, when resource created.

    Args:
        name (str): human-readable name of the file.
            Default: guess using upload field
        upload (shared.types.Uploadable): content of the file as bytes,
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
    return tk.get_action("files_file_create")(
        Context(context, ignore_auth=True),
        dict(data_dict, storage=storage_name),
    )
