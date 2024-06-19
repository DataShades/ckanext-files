from __future__ import annotations

from typing import Any, cast

import sqlalchemy as sa
from werkzeug.utils import secure_filename

import ckan.plugins.toolkit as tk
from ckan import model
from ckan.logic import validate
from ckan.types import Action, Context

from ckanext.files import shared
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
@validate(schema.file_search_by_user)
def files_file_search_by_user(  # noqa: C901
    context: Context,
    data_dict: dict[str, Any],
) -> dict[str, Any]:
    """Internal action. Do not use it."""

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

    Params:

    * `start`: index of first row in result/number of rows to skip. Default: `0`
    * `rows`: number of rows to return. Default: `10`
    * `sort`: name of File column used for sorting. Default: `name`
    * `reverse`: sort results in descending order. Default: `False`
    * `storage_data`: mask for `storage_data` column. Default: `{}`
    * `plugin_data`: mask for `plugin_data` column. Default: `{}`
    * `owner_type: str`: show only specific owner id if present. Default: `None`
    * `owner_type`: show only specific owner type if present. Default: `None`
    * `pinned`: show only pinned/unpinned items if present. Default: `None`
    * `completed`: use `False` to search incomplete uploads. Default: `True`

    Returns:

    * `count`: total number of files mathing filters
    * `results`: array of dictionaries with file details.

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

    return {"count": total, "results": [f.dictize(context) for f in sess.scalars(stmt)]}


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

    ```python
    ckanapi action files_file_create upload@path/to/file.txt
    ```

    When uploading a raw content of the file using string or bytes object, name
    is mandatory.

    ```python
    ckanapi action files_file_create upload@<(echo -n "hello world") name=file.txt
    ```

    Requires storage with `CREATE` capability.

    Params:

    * `name`: human-readable name of the file. Default: guess using upload field
    * `storage`: name of the storage that will handle the upload. Default: `default`
    * `upload`: content of the file as string, bytes, file descriptor or uploaded file

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
        storage_data=storage_data,
    )
    storage_data.into_model(fileobj)
    context["session"].add(fileobj)

    _set_user_owner(context, "file", fileobj.id)
    context["session"].commit()

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

    Params:

    * `id`: ID of the file
    * `completed`: use `False` to remove incomplete uploads. Default: `True`

    Returns:

    dictionary with details of the removed file.
    """

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

    Params:

    * `id`: ID of the file
    * `completed`: use `False` to show incomplete uploads. Default: `True`

    Returns:

    dictionary with file details

    """

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
    """Rename the file.

    This action changes human-readable name of the file, which is stored in
    DB. Real location of the file in the storage is not modified.

    ```sh
    ckanapi action files_file_show \\
        id=226056e2-6f83-47c5-8bd2-102e2b82ab9a \\
        name=new-name.txt
    ```

    Params:

    * `id`: ID of the file
    * `name`: new name of the file
    * `completed`: use `False` to rename incomplete uploads. Default: `True`

    Returns:

    dictionary with file details

    """

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
    """Initialize multipart(resumable,continuous,signed,etc) upload.

    Apart from standard parameters, different storages can require additional
    data, so always check documentation of the storage before initiating
    multipart upload.

    When upload initialized, storage usually returns details required for
    further upload. It may be a presigned URL for direct upload, or just an ID
    of upload which must be used with `files_multipart_update`.

    Requires storage with `MULTIPART` capability.

    Params:

    * `storage`: name of the storage that will handle the upload. Default: `default`
    * `name`: name of the uploaded file.
    * `content_type`: MIMEtype of the uploaded file. Used for validation
    * `size`: Expected size of upload. Used for validation
    * `hash`: Expected content hash. If present, used for validation.

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

    Params:

    * `id`: ID of the incomplete upload

    Returns:

    dictionary with details of the updated upload

    """

    tk.check_access("files_multipart_refresh", context, data_dict)

    fileobj = context["session"].get(Multipart, data_dict["id"])
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

    Params:

    * `id`: ID of the incomplete upload

    Returns:

    dictionary with details of the updated upload

    """

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

    Params:

    * `id`: ID of the incomplete upload

    Returns:

    dictionary with details of the created file

    """
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
    except shared.exc.UploadError as err:
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
    """Transfer file ownership.

    Depending on storage this action may require additional parameters. Most
    likely, `upload` with the fragment of uploaded file.

    Params:

    * `id`: ID of the file upload
    * `completed`: use `False` to transfer incomplete uploads. Default: `True`
    * `owner_id`: ID of the new owner
    * `owner_type`: type of the new owner
    * `force`: move file even if it's pinned. Default: `False`
    * `pin`: pin file after transfer to stop future transfers. Default: `False`

    Returns:

    dictionary with details of updated file
    """

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

    Params:

    * `id`: ID of the file
    * `completed`: use `False` to pin incomplete uploads. Default: `True`

    Returns:

    dictionary with details of updated file

    """

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
    """Pin file to the current owner.

    Pinned file cannot be transfered to a different owner. Use it to guarantee
    that file referred by entity is not accidentally transferred to a different
    owner.

    Params:

    * `id`: ID of the file
    * `completed`: use `False` to unpin incomplete uploads. Default: `True`

    Returns:

    dictionary with details of updated file

    """
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


@validate(schema.resource_upload)
def files_resource_upload(context: Context, data_dict: dict[str, Any]):
    """Create a new file inside resource storage.

    This action internally calls `files_file_create` with `ignore_auth=True`
    and always uses resources storage.

    New file is not attached to resource. You need to call
    `files_transfer_ownership` manually, when resource created.

    Params:

    * `name`: human-readable name of the file. Default: guess using upload field
    * `upload`: content of the file as string, bytes, file descriptor or uploaded file

    Returns:

    dictionary with file details.

    """

    tk.check_access("files_resource_upload", context, data_dict)
    storage_name = shared.config.resources_storage()
    if not storage_name:
        raise tk.ValidationError(
            {"upload": ["Resource uploads are not supported"]},
        )

    return tk.get_action("files_file_create")(
        Context(context, ignore_auth=True),
        dict(data_dict, storage=storage_name),
    )
