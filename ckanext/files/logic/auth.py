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

    result = authz.is_authorized(func_name, tk.fresh_context(context), {"id": owner_id})
    return result["success"]


def _file_allows(
    context: Context,
    file: shared.File,
    operation: types.FileOperation,
) -> bool:
    """Decide if user is allowed to perform operation on file."""
    for plugin in p.PluginImplementations(interfaces.IFiles):
        result = plugin.files_file_allows(context, file, operation)
        if result is not None:
            return result

    info = file.owner if file else None

    if not info:
        return False

    cascade = shared.config.cascade_access()
    if info.owner_type not in cascade:
        return False

    if cascade[info.owner_type] and file.storage not in cascade[info.owner_type]:
        return False

    func_name = f"{info.owner_type}_{operation}"

    result = authz.is_authorized(
        func_name,
        tk.fresh_context(context),
        {"id": info.owner_id},
    )

    return result["success"]


def _get_user(context: Context) -> model.User | None:
    user = context.get("auth_user_obj")
    if isinstance(user, model.User):
        return user

    if tk.current_user and tk.current_user.name == context["user"]:
        return cast(model.User, tk.current_user)

    cache = utils.ContextCache(context)
    return cache.get("user", context["user"], lambda: model.User.get(context["user"]))


def _get_file(context: Context, file_id: str) -> shared.File | None:
    cache = utils.ContextCache(context)
    return cache.get_model("file", file_id, shared.File)


# Permissions #################################################################


@tk.auth_allow_anonymous_access
def files_permission_manage_files(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Check if user is allowed to manage any file.

    This is a sort of "sysadmin" check in terms of file management. Give this
    permission to user who needs an access to every owned, unowned, hidden,
    incomplete and private file
    """
    return {"success": False, "msg": "Not allowed to manage files"}


@tk.auth_allow_anonymous_access
def files_permission_owns_file(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Check if user is allowed to manage a file.

    Normally, owner of the file passes this check as well as any user who has
    ``files_permission_manage_files``.
    """
    if authz.is_authorized_boolean("files_permission_manage_files", context, data_dict):
        return {"success": True}

    not_an_owner = "Not an owner of the file"
    user = _get_user(context)
    if not user:
        return {"success": False, "msg": not_an_owner}

    file = _get_file(context, data_dict["id"])
    if not file or not file.owner:
        return {"success": False, "msg": not_an_owner}

    return {
        "success": file.owner.owner_type == "user" and file.owner.owner_id == user.id,
        "msg": not_an_owner,
    }


@tk.auth_allow_anonymous_access
def files_permission_edit_file(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Check if user is allowed to edit a file.

    Owners and global managers can edit files. Additionally plugins can extend
    this permission via ``IFiles.files_file_allows`` hook.

    """
    result = authz.is_authorized_boolean("files_permission_owns_file", context, data_dict)
    if not result:
        file = _get_file(context, data_dict["id"])
        result = bool(file and _file_allows(context, file, "update"))

    return {"success": result, "msg": "Not allowed to edit file"}


@tk.auth_allow_anonymous_access
def files_permission_delete_file(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Check if user is allowed to delete the file.

    Owners and global managers can delete files. Additionally plugins can extend
    this permission via ``IFiles.files_file_allows`` hook.

    """
    result = authz.is_authorized_boolean("files_permission_owns_file", context, data_dict)
    if not result:
        file = _get_file(context, data_dict["id"])
        result = bool(file and _file_allows(context, file, "delete"))

    return {"success": result, "msg": "Not allowed to delete file"}


@tk.auth_allow_anonymous_access
def files_permission_read_file(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Check if user is allowed to read a file.

    Owners and global managers can read files. Additionally plugins can extend
    this permission via ``IFiles.files_file_allows`` hook.

    """
    result = authz.is_authorized_boolean("files_permission_owns_file", context, data_dict)
    if not result:
        file = _get_file(context, data_dict["id"])
        result = bool(file and _file_allows(context, file, "show"))

    return {"success": result, "msg": "Not allowed to read file"}


@tk.auth_allow_anonymous_access
def files_permission_download_file(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Check if user is allowed to download a file.

    Owners and global managers can download files. Additionally plugins can extend
    this permission via ``IFiles.files_file_allows`` hook.

    """
    result = authz.is_authorized_boolean("files_permission_read_file", context, data_dict)
    return {"success": result, "msg": "Not allowed to read file"}


# API #########################################################################


@tk.auth_allow_anonymous_access
def files_file_search(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Only file manager can search files."""
    return authz.is_authorized("files_permission_manage_files", context, data_dict)


@tk.auth_allow_anonymous_access
def files_file_create(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    if context["user"] and (
        shared.config.authenticated_uploads() and data_dict["storage"] in shared.config.authenticated_storages()
    ):
        return {"success": True}

    return authz.is_authorized("files_permission_manage_files", context, data_dict)


@tk.auth_allow_anonymous_access
def files_file_register(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Check if user can register files from storage in DB.

    Only file manager can register files.
    """
    return authz.is_authorized("files_permission_manage_files", context, data_dict)


@tk.auth_allow_anonymous_access
def files_file_delete(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Only owner can remove files."""
    return authz.is_authorized("files_permission_delete_file", context, data_dict)


@tk.auth_allow_anonymous_access
def files_file_show(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Only owner can view files."""
    return authz.is_authorized("files_permission_read_file", context, data_dict)


@tk.auth_allow_anonymous_access
def files_file_rename(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Only owner can rename files."""
    return authz.is_authorized("files_permission_edit_file", context, data_dict)


@tk.auth_allow_anonymous_access
def files_file_pin(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    return authz.is_authorized("files_permission_edit_file", context, data_dict)


@tk.auth_allow_anonymous_access
def files_file_unpin(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    return authz.is_authorized("files_permission_edit_file", context, data_dict)


@tk.auth_allow_anonymous_access
def files_transfer_ownership(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Only file manager can transfer ownership."""
    file = _get_file(context, data_dict["id"])
    if not file or (file.owner and file.owner.pinned and not data_dict["force"]):
        return {"success": False, "msg": "File is pinned"}

    result = authz.is_authorized_boolean("files_permission_manage_files", context, data_dict)
    if not result:
        result = bool(
            authz.is_authorized_boolean("files_permission_edit_file", context, data_dict)
            and _owner_allows(
                context,
                data_dict["owner_type"],
                data_dict["owner_id"],
                "file_transfer",
            ),
        )

    return {"success": result, "msg": "Not allowed to edit file"}


@tk.auth_allow_anonymous_access
def files_file_scan(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Only file owner can list files."""
    result = authz.is_authorized_boolean("files_permission_manage_files", context, data_dict)
    if not result:
        result = _owner_allows(
            context,
            data_dict["owner_type"],
            data_dict["owner_id"],
            "file_scan",
        )

    return {"success": result, "msg": "Not allowed to list files"}


# not included into CKAN ######################################################


@tk.auth_allow_anonymous_access
def files_resource_upload(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Users can upload resources files."""
    # TODO: add restriction on number of free-files or their total size inside
    # resource storage.
    try:
        shared.get_storage(shared.config.resources_storage())
    except shared.exc.UnknownStorageError:
        return {"success": False}

    if data_dict.get("resource_id"):
        return authz.is_authorized("resource_update", context, {"id": data_dict["resource_id"]})

    return authz.is_authorized("resource_create", context, data_dict)


@tk.auth_allow_anonymous_access
def files_autocomplete_available_resource_files(
    context: Context,
    data_dict: dict[str, Any],
) -> AuthResult:
    """Users allowed to search their free resource files."""
    return {"success": True}


@tk.auth_allow_anonymous_access
def files_file_replace(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Only owner can replace files."""
    return authz.is_authorized("files_permission_edit_file", context, data_dict)


@tk.auth_allow_anonymous_access
def files_multipart_refresh(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    return authz.is_authorized("files_permission_edit_file", context, data_dict)


@tk.auth_allow_anonymous_access
def files_multipart_start(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    return authz.is_authorized("files_file_create", context, data_dict)


@tk.auth_allow_anonymous_access
def files_multipart_update(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    return authz.is_authorized("files_permission_edit_file", context, data_dict)


@tk.auth_allow_anonymous_access
def files_multipart_complete(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    return authz.is_authorized("files_permission_edit_file", context, data_dict)
