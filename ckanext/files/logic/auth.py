from __future__ import annotations

from typing import Any, cast

import ckan.plugins.toolkit as tk
from ckan import authz, model
from ckan.types import AuthResult, Context

from ckanext.files import base, config, utils
from ckanext.files.model import File, Multipart


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
) -> File | Multipart | None:
    if "files_file" not in context:
        context["files_file"] = model.Session.get(  # type: ignore
            File if completed else Multipart,
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
    result = base.is_allowed(context, file, file and file.owner, "update")
    if result is None:
        return authz.is_authorized("files_owns_file", context, data_dict)

    return {"success": result, "msg": "Not allowed to edit file"}


@tk.auth_disallow_anonymous_access
def files_read_file(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    file = _get_file(context, data_dict["id"], data_dict.get("completed", True))
    result = base.is_allowed(context, file, file and file.owner, "show")
    if result is None:
        return authz.is_authorized("files_edit_file", context, data_dict)

    return {"success": result, "msg": "Not allowed to read file"}


@tk.auth_disallow_anonymous_access
def files_delete_file(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    file = _get_file(context, data_dict["id"], data_dict.get("completed", True))
    result = base.is_allowed(context, file, file and file.owner, "delete")
    if result is None:
        return authz.is_authorized("files_edit_file", context, data_dict)

    return {"success": result, "msg": "Not allowed to delete file"}


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
        config.authenticated_uploads()
        and data_dict["storage"] in config.authenticated_storages()
    ):
        return {"success": True}

    return authz.is_authorized("files_manage_files", context, data_dict)


def files_file_delete(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Only owner can remove files."""
    return authz.is_authorized("files_delete_file", context, data_dict)


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
    result = base.is_allowed(context, file, owner, "file_transfer")

    if result is None:
        return authz.is_authorized("files_manage_files", context, data_dict)

    return {"success": result, "msg": "Not allowed to edit file"}
