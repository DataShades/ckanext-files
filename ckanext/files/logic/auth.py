from __future__ import annotations

from typing import Any, cast

import sqlalchemy as sa

import ckan.plugins.toolkit as tk
from ckan import authz, model
from ckan.types import AuthResult, Context

from ckanext.files.model import Owner


def _get_user(context: Context) -> model.User | None:
    if "auth_user_obj" in context:
        return cast(model.User, context["auth_user_obj"])

    user = tk.current_user if tk.current_user.is_authenticated else None

    if user and context["user"] == user.name:
        return cast(model.User, user)

    return model.User.get(context["user"])


def _is_owner(user_id: str, file_id: str) -> bool:
    stmt = Owner.owners_of(file_id, "file").where(
        sa.and_(
            Owner.owner_type == "user",
            Owner.owner_id == user_id,
            Owner.access == Owner.ACCESS_FULL,
        ),
    )
    return model.Session.query(stmt.exists()).scalar()


@tk.auth_disallow_anonymous_access
def files_manage_files(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    return {"success": False}


@tk.auth_disallow_anonymous_access
def files_owns_file(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    user = _get_user(context)
    is_manager = authz.is_authorized_boolean("files_manage_files", context, data_dict)
    is_owner = bool(user and _is_owner(user.id, data_dict["id"]))

    return {
        "success": is_owner or is_manager,
        "msg": "Not an owner of the file",
    }


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


@tk.auth_disallow_anonymous_access
def files_file_search(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Only file manager can search files."""
    return authz.is_authorized("files_manage_files", context, data_dict)


@tk.auth_disallow_anonymous_access
def files_file_create(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    return authz.is_authorized("files_manage_files", context, data_dict)


@tk.auth_disallow_anonymous_access
def files_file_delete(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Only owner can remove files."""
    return authz.is_authorized("files_owns_file", context, data_dict)


@tk.auth_disallow_anonymous_access
def files_file_show(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Only owner can view files."""
    return authz.is_authorized("files_owns_file", context, data_dict)


@tk.auth_disallow_anonymous_access
def files_file_download(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Only owner can download files."""
    return authz.is_authorized("files_owns_file", context, data_dict)


@tk.auth_disallow_anonymous_access
def files_file_rename(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    """Only owner can rename files."""
    return authz.is_authorized("files_owns_file", context, data_dict)


@tk.auth_disallow_anonymous_access
def files_multipart_refresh(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    return authz.is_authorized("files_owns_file", context, data_dict)


@tk.auth_disallow_anonymous_access
def files_multipart_start(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    return authz.is_authorized("files_file_create", context, data_dict)


@tk.auth_disallow_anonymous_access
def files_multipart_update(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    return authz.is_authorized("files_owns_file", context, data_dict)


@tk.auth_disallow_anonymous_access
def files_multipart_complete(context: Context, data_dict: dict[str, Any]) -> AuthResult:
    return authz.is_authorized("files_owns_file", context, data_dict)
