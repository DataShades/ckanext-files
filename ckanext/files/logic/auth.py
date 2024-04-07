import sqlalchemy as sa

import ckan.plugins.toolkit as tk
from ckan import authz, model

from ckanext.files.model import Owner
from ckanext.files.utils import make_collector

from ckanext.files import types  # isort: skip # noqa: F401


_auth_functions, auth = make_collector()


def get_auth_functions():
    return dict(_auth_functions)


def _get_user(context):
    # type: (types.Any) -> model.User | None
    if "auth_user_obj" in context:
        return context["auth_user_obj"]

    if tk.check_ckan_version("2.10"):
        user = tk.current_user if tk.current_user.is_authenticated else None
    else:
        user = tk.g.userobj  # type: types.Any

    if user and context["user"] == user.name:
        return user

    return model.User.get(context["user"])


def _is_owner(user_id, file_id):
    # type: (str, str) -> bool
    stmt = Owner.owners_of(file_id, "file").where(
        sa.and_(
            Owner.owner_type == "user",
            Owner.owner_ie == user_id,
        ),
    )
    return model.Session.query(stmt.exists()).scalar()


@auth
@tk.auth_disallow_anonymous_access
def files_manage_files(context, data_dict):
    # type: (types.Any, dict[str, types.Any]) -> types.Any
    return {"success": False}


@auth
@tk.auth_disallow_anonymous_access
def files_owns_file(context, data_dict):
    # type: (types.Any, dict[str, types.Any]) -> types.Any
    user = _get_user(context)
    is_owner = bool(user and _is_owner(user.id, data_dict["id"]))

    return {"success": is_owner, "msg": "Not an owner of the file"}


@auth
@tk.auth_disallow_anonymous_access
def files_file_search_by_user(context, data_dict):
    # type: (types.Any, dict[str, types.Any]) -> types.Any
    """Only user himself can view his own files."""

    # `user` from context will be used used when it's not in data_dict, so it's
    # an access to own files
    if "user" not in data_dict:
        return {"success": True}

    user = _get_user(context)

    return {
        "success": user and data_dict["user"] in [user.name, user.id],
        "msg": "Not authorized to view files of this user",
    }


@auth
@tk.auth_disallow_anonymous_access
def files_file_create(context, data_dict):
    # type: (types.Any, dict[str, types.Any]) -> types.Any
    return {"success": True}


@auth
@tk.auth_disallow_anonymous_access
def files_file_delete(context, data_dict):
    # type: (types.Any, dict[str, types.Any]) -> types.Any
    """Only owner can remove files."""
    return authz.is_authorized("files_owns_file", context, data_dict)


@auth
@tk.auth_disallow_anonymous_access
def files_file_show(context, data_dict):
    # type: (types.Any, dict[str, types.Any]) -> types.Any
    """Only owner can view files."""
    return authz.is_authorized("files_owns_file", context, data_dict)


@auth
@tk.auth_disallow_anonymous_access
def files_file_rename(context, data_dict):
    # type: (types.Any, dict[str, types.Any]) -> types.Any
    """Only owner can rename files."""
    return authz.is_authorized("files_owns_file", context, data_dict)


@auth
@tk.auth_disallow_anonymous_access
def files_upload_show(context, data_dict):
    # type: (types.Any, dict[str, types.Any]) -> types.Any
    return authz.is_authorized("files_owns_file", context, data_dict)


@auth
@tk.auth_disallow_anonymous_access
def files_upload_initialize(context, data_dict):
    # type: (types.Any, dict[str, types.Any]) -> types.Any
    return authz.is_authorized("files_file_create", context, data_dict)


@auth
@tk.auth_disallow_anonymous_access
def files_upload_update(context, data_dict):
    # type: (types.Any, dict[str, types.Any]) -> types.Any
    return authz.is_authorized("files_owns_file", context, data_dict)


@auth
@tk.auth_disallow_anonymous_access
def files_upload_complete(context, data_dict):
    # type: (types.Any, dict[str, types.Any]) -> types.Any
    return authz.is_authorized("files_owns_file", context, data_dict)
