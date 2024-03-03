import six
import datetime
import os


from werkzeug.utils import secure_filename
import ckan.plugins.toolkit as tk
from ckan.logic import validate
from ckan.lib.uploader import get_uploader, get_storage_path

from ckanext.files import shared, exceptions
from ckanext.files.storage import Capability
from ckanext.files.utils import make_collector
from ckanext.files.model import File
from . import schema

if six.PY3:
    from typing import Any

_actions, action = make_collector()


def get_actions():
    return dict(_actions)


def files_uploader(kind, old_filename=None):
    # type: (str, str | None) -> Any
    return get_uploader(kind, old_filename)


@action
@validate(schema.file_create)
def files_file_create(context, data_dict):
    # type: (Any, dict[str, Any]) -> dict[str, Any]
    tk.check_access("files_file_create", context, data_dict)

    extras = data_dict.get("__extras", {})
    name = secure_filename(data_dict["name"])

    try:
        storage = shared.get_storage(data_dict["storage"])
    except exceptions.UnknownStorageError as err:
        raise tk.ValidationError({"storage": [str(err)]})

    if not storage.supports(Capability.CREATE):
        raise tk.ValidationError({"storage": ["Operation is not supported"]})

    storage_data = storage.upload(name, data_dict["upload"], extras)
    fileobj = File(name=name, storage=data_dict["storage"], storage_data=storage_data)

    context["session"].add(fileobj)
    if not context.get("defer_commit"):
        context["session"].commit()

    return fileobj.dictize(context)


@action
@validate(schema.file_delete)
def files_file_delete(context, data_dict):
    # type: (Any, dict[str, Any]) -> bool
    tk.check_access("files_file_delete", context, data_dict)

    data_dict["id"]
    fileobj = context["session"].get(File, data_dict["id"])
    if not fileobj:
        raise tk.ObjectNotFound("file")

    storage = shared.get_storage(fileobj.storage)
    if not storage.supports(Capability.REMOVE):
        raise tk.ValidationError({"storage": ["Operation is not supported"]})

    storage.remove(fileobj.storage_data)
    context["session"].delete(fileobj)
    if not context.get("defer_commit"):
        context["session"].commit()

    return fileobj.dictize(context)


@action
@validate(schema.file_show)
def files_file_show(context, data_dict):
    # type: (Any, dict[str, Any]) -> dict[str, Any]
    tk.check_access("files_file_show", context, data_dict)

    data_dict["id"]
    fileobj = context["session"].get(File, data_dict["id"])
    if not fileobj:
        raise tk.ObjectNotFound("file")

    if context.get("update_access_time"):
        fileobj.access()
        if not context.get("defer_commit"):
            context["session"].commit()

    return fileobj.dictize(context)
