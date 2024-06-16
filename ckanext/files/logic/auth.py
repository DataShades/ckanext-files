from __future__ import annotations

from typing import Any, cast

import ckan.plugins as p
import ckan.plugins.toolkit as tk
from ckan import authz, model
from ckan.types import AuthResult, Context

from ckanext.files import interfaces, shared, types, utils


def _is_allowed(
    context: Context,
    file: shared.File | shared.Multipart | None,
    operation: types.AuthOperation,
    next_owner: Any | None = None,
) -> Any:
    """Decide if user is allowed to perform operation on file."""
    info = file.owner_info if file else None

    if info and info.owner_type in shared.config.cascade_access():
        if operation == "file_transfer" and shared.config.transfer_as_update():
            func_name = f"{info.owner_type}_update"
        else:
            func_name = f"{info.owner_type}_{operation}"

        try:
            tk.check_access(
                func_name,
                context,
                {"id": info.owner_id},
            )

        except tk.NotAuthorized:
            return False

        except ValueError:
            pass

    for plugin in p.PluginImplementations(interfaces.IFiles):
        result = plugin.files_is_allowed(context, file, operation, next_owner)
        if result is not None:
            return result


def _get_user(context: Context) -> model.User | None:
    if "auth_user_obj" in context:
        return cast(model.User, context["auth_user_obj"])

    user = tk.current_user if tk.current_user.is_authenticated else None

    if user and context["user"] == user.name:
        return cast(model.User, user)

    return model.User.get(context["user"])


def _get_file(
    context: Context,
    file_id: str,
    completed: bool,
) -> shared.File | shared.Multipart | None:
    if "files_file" not in context:
        context["files_file"] = model.Session.get(  # type: ignore
            shared.File if completed else shared.Multipart,
            file_id,
        )

    return context["files_file"]  # type: ignore


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
    file = _get_file(context, data_dict["id"], data_dict.get("completed", True))
    result = _is_allowed(context, file, "update")
    if result is None:
        return authz.is_authorized("files_owns_file", context, data_dict)

    return {"success": result, "msg": "Not allowed to edit file"}


@tk.auth_disallow_anonymous_access
def files_read_file(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    file = _get_file(context, data_dict["id"], data_dict.get("completed", True))
    result = _is_allowed(context, file, file and file.owner, "show")
    if result is None:
        return authz.is_authorized("files_edit_file", context, data_dict)

    return {"success": result, "msg": "Not allowed to read file"}


@tk.auth_disallow_anonymous_access
def files_file_search_by_user(
    context: Context,
    data_dict: dict[str, Any],
) -> AuthResult:
    """Only user himself can view his own files."""

    # `user` from context will be used used when it's not in data_dict, so it's
    # an access to own files
    if "user" not in data_dict:
        return {"success": True}

    user = _get_user(context)

    return {
        "success": bool(user) and data_dict["user"] in [user.name, user.id],
        "msg": "Not authorized to view files of this user",
    }


def files_file_search(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Only file manager can search files."""
    return authz.is_authorized("files_manage_files", context, data_dict)


@tk.auth_disallow_anonymous_access
def files_file_create(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    if (
        shared.config.authenticated_uploads()
        and data_dict["storage"] in shared.config.authenticated_storages()
    ):
        return {"success": True}

    return authz.is_authorized("files_manage_files", context, data_dict)


@tk.auth_disallow_anonymous_access
def files_file_delete(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Only owner can remove files."""
    file = _get_file(context, data_dict["id"], data_dict.get("completed", True))
    result = _is_allowed(context, file, "delete")
    if result is None:
        return authz.is_authorized("files_edit_file", context, data_dict)

    return {"success": result, "msg": "Not allowed to delete file"}


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

    owner = utils.get_owner(data_dict["owner_type"], data_dict["owner_id"])
    result = _is_allowed(context, file, "file_transfer", owner)

    if result is None:
        return authz.is_authorized("files_manage_files", context, data_dict)

    return {"success": result, "msg": "Not allowed to edit file"}


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
