from __future__ import annotations

from typing import Any, cast

import ckan.plugins as p
import ckan.plugins.toolkit as tk
from ckan import authz, model
from ckan.types import AuthResult, Context

from ckanext.files import interfaces, shared, types, utils


def _owner_allows(
    context: Context,
    owner_type: str,
    owner_id: str,
    operation: types.OwnerOperation,
) -> bool:
    """Decide if user is allowed to perform operation on owner."""
    for plugin in p.PluginImplementations(interfaces.IFiles):
        result = plugin.files_owner_allows(context, owner_type, owner_id, operation)
        if result is not None:
            return result

    if (operation == "file_transfer" and shared.config.transfer_as_update()) or (
        operation == "file_scan" and shared.config.scan_as_update()
    ):
        func_name = f"{owner_type}_update"

    else:
        func_name = f"{owner_type}_{operation}"

    try:
        tk.check_access(
            func_name,
            tk.fresh_context(context),
            {"id": owner_id},
        )

    except (tk.NotAuthorized, ValueError):
        return False

    return True


def _file_allows(
    context: Context,
    file: shared.File | shared.Multipart,
    operation: types.FileOperation,
) -> bool:
    """Decide if user is allowed to perform operation on file."""
    for plugin in p.PluginImplementations(interfaces.IFiles):
        result = plugin.files_file_allows(context, file, operation)
        if result is not None:
            return result

    info = file.owner_info if file else None

    if not info or info.owner_type not in shared.config.cascade_access():
        return False

    func_name = f"{info.owner_type}_{operation}"

    try:
        tk.check_access(
            func_name,
            tk.fresh_context(context),
            {"id": info.owner_id},
        )

    except (tk.NotAuthorized, ValueError):
        return False

    return True


def _get_user(context: Context) -> model.User | None:
    if "auth_user_obj" in context:
        return cast(model.User, context["auth_user_obj"])

    user = tk.current_user if tk.current_user.is_authenticated else None

    if user and context["user"] == user.name:
        return cast(model.User, user)

    cache = utils.ContextCache(context)
    return cache.get("user", context["user"], lambda: model.User.get(context["user"]))


def _get_file(
    context: Context,
    file_id: str,
    completed: bool,
) -> shared.File | shared.Multipart | None:
    cache = utils.ContextCache(context)
    return cache.get_model(
        "file",
        file_id,
        shared.File if completed else shared.Multipart,
    )


@tk.auth_disallow_anonymous_access
def files_manage_files(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    return {"success": False}


@tk.auth_disallow_anonymous_access
def files_owns_file(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    if authz.is_authorized_boolean("files_manage_files", context, data_dict):
        return {"success": True}

    user = _get_user(context)
    if not user:
        return {
            "success": False,
            "msg": "Not an owner of the file",
        }

    file = _get_file(context, data_dict["id"], data_dict.get("completed", True))
    if not file or not file.owner_info:
        return {
            "success": False,
            "msg": "Not an owner of the file",
        }

    return {
        "success": file.owner_info.owner_type == "user"
        and file.owner_info.owner_id == user.id,
        "msg": "Not an owner of the file",
    }


@tk.auth_disallow_anonymous_access
def files_edit_file(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    result = authz.is_authorized_boolean("files_owns_file", context, data_dict)
    if not result:
        file = _get_file(context, data_dict["id"], data_dict.get("completed", True))
        result = bool(file and _file_allows(context, file, "update"))

    return {"success": result, "msg": "Not allowed to edit file"}


@tk.auth_disallow_anonymous_access
def files_read_file(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    result = authz.is_authorized_boolean("files_owns_file", context, data_dict)
    if not result:
        file = _get_file(context, data_dict["id"], data_dict.get("completed", True))
        result = bool(file and _file_allows(context, file, "show"))

    return {"success": result, "msg": "Not allowed to read file"}


def files_file_search(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Only file manager can search files."""
    return authz.is_authorized("files_manage_files", context, data_dict)


def files_file_create(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    if (
        shared.config.authenticated_uploads()
        and data_dict["storage"] in shared.config.authenticated_storages()
    ):
        return {"success": True}

    return authz.is_authorized("files_manage_files", context, data_dict)


def files_file_delete(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Only owner can remove files."""
    result = authz.is_authorized_boolean("files_owns_file", context, data_dict)
    if not result:
        file = _get_file(context, data_dict["id"], data_dict.get("completed", True))
        result = bool(file and _file_allows(context, file, "delete"))

    return {"success": result, "msg": "Not allowed to delete file"}


def files_file_replace(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Only owner can replace files."""
    return authz.is_authorized("files_edit_file", context, data_dict)


def files_file_show(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Only owner can view files."""
    return authz.is_authorized("files_read_file", context, data_dict)


def files_file_download(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Only owner can download files."""
    return authz.is_authorized("files_read_file", context, data_dict)


def files_file_rename(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Only owner can rename files."""
    return authz.is_authorized("files_edit_file", context, data_dict)


def files_multipart_refresh(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    return authz.is_authorized(
        "files_edit_file",
        context,
        dict(data_dict, completed=False),
    )


def files_multipart_start(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    return authz.is_authorized(
        "files_file_create",
        context,
        dict(data_dict, completed=False),
    )


def files_multipart_update(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    return authz.is_authorized(
        "files_edit_file",
        context,
        dict(data_dict, completed=False),
    )


def files_multipart_complete(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    return authz.is_authorized(
        "files_edit_file",
        context,
        dict(data_dict, completed=False),
    )


def files_file_pin(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    return authz.is_authorized(
        "files_edit_file",
        context,
        dict(data_dict, completed=False),
    )


def files_file_unpin(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    return authz.is_authorized(
        "files_edit_file",
        context,
        dict(data_dict, completed=False),
    )


def files_transfer_ownership(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Only file manager can transfer ownership."""
    file = _get_file(context, data_dict["id"], data_dict.get("completed", True))
    if file and file.owner_info and file.owner_info.pinned and not data_dict["force"]:
        return {"success": False, "msg": "File is pinned"}

    result = authz.is_authorized_boolean("files_manage_files", context, data_dict)
    if not result:
        result = bool(
            file
            and _file_allows(context, file, "update")
            and _owner_allows(
                context,
                data_dict["owner_type"],
                data_dict["owner_id"],
                "file_transfer",
            ),
        )

    return {"success": result, "msg": "Not allowed to edit file"}


def files_file_scan(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Only file owner can list files."""
    result = authz.is_authorized_boolean("files_manage_files", context, data_dict)
    if not result:
        result = _owner_allows(
            context,
            data_dict["owner_type"],
            data_dict["owner_id"],
            "file_scan",
        )

    return {"success": result, "msg": "Not allowed to list files"}


@tk.auth_disallow_anonymous_access
def files_resource_upload(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Users can upload resources files."""
    # TODO: add restriction on number of free-files or their total size inside
    # resource storage.
    try:
        shared.get_storage(shared.config.resources_storage())
    except shared.exc.UnknownStorageError:
        return {"success": False}

    return {"success": True}


@tk.auth_disallow_anonymous_access
def files_group_image_upload(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Users can upload group images."""
    # TODO: add restriction on number of free-files or their total size inside
    # resource storage.

    try:
        shared.get_storage(shared.config.group_images_storage())
    except shared.exc.UnknownStorageError:
        return {"success": False}

    return {"success": True}


@tk.auth_disallow_anonymous_access
def files_user_image_upload(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Users can upload avatars."""
    # TODO: add restriction on number of free-files or their total size inside
    # resource storage.
    try:
        shared.get_storage(shared.config.user_images_storage())
    except shared.exc.UnknownStorageError:
        return {"success": False}

    return {"success": True}


@tk.auth_disallow_anonymous_access
def files_autocomplete_available_resource_files(
    context: Context,
    data_dict: dict[str, Any],
) -> AuthResult:
    """Users allowed to search their free resource files."""
    return {"success": True}
