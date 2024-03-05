import six

from ckan import authz

from ckanext.files.utils import make_collector

if six.PY3:
    from typing import Any  # isort: skip # noqa: F401


_auth_functions, auth = make_collector()


def get_auth_functions():
    return dict(_auth_functions)


@auth
def files_manage_files(context, data_dict):
    # type: (Any, dict[str, Any]) -> Any
    return {"success": False}


@auth
def files_file_create(context, data_dict):
    # type: (Any, dict[str, Any]) -> Any
    return authz.is_authorized("files_manage_files", context, data_dict)


@auth
def files_file_delete(context, data_dict):
    # type: (Any, dict[str, Any]) -> Any
    return authz.is_authorized("files_manage_files", context, data_dict)


@auth
def files_file_show(context, data_dict):
    # type: (Any, dict[str, Any]) -> Any
    return authz.is_authorized("files_manage_files", context, data_dict)


@auth
def files_upload_initialize(context, data_dict):
    # type: (Any, dict[str, Any]) -> Any
    return authz.is_authorized("files_manage_files", context, data_dict)


@auth
def files_upload_update(context, data_dict):
    # type: (Any, dict[str, Any]) -> Any
    return authz.is_authorized("files_manage_files", context, data_dict)


@auth
def files_upload_complete(context, data_dict):
    # type: (Any, dict[str, Any]) -> Any
    return authz.is_authorized("files_manage_files", context, data_dict)
