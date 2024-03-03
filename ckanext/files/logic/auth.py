import six
from ckanext.files.utils import make_collector

if six.PY3:
    from typing import Any

_auth_functions, auth = make_collector()


def get_auth_functions():
    return dict(_auth_functions)


@auth
def files_file_create(context, data_dict):
    # type: (Any, dict[str, Any]) -> Any
    return {"success": False}


@auth
def files_file_delete(context, data_dict):
    # type: (Any, dict[str, Any]) -> Any
    return {"success": False}


@auth
def files_file_show(context, data_dict):
    # type: (Any, dict[str, Any]) -> Any
    return {"success": True}


@auth
def files_get_unused_files(context, data_dict):
    # type: (Any, dict[str, Any]) -> Any
    return {"success": False}
