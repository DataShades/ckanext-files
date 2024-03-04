import six
from werkzeug.utils import secure_filename

import ckan.plugins.toolkit as tk
from ckan.logic import validate

from ckanext.files import exceptions, shared
from ckanext.files.model import File, Upload
from ckanext.files.storage import Capability
from ckanext.files.utils import make_collector

from . import schema

if six.PY3:
    from typing import Any  # isort: skip

_actions, action = make_collector()


def get_actions():
    return dict(_actions)


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

    try:
        storage_data = storage.upload(name, data_dict["upload"], extras)
    except exceptions.LargeUploadError as err:
        raise tk.ValidationError({"upload": [str(err)]})

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


@action
@validate(schema.upload_initialize)
def files_upload_initialize(context, data_dict):
    # type: (Any, dict[str, Any]) -> dict[str, Any]
    tk.check_access("files_upload_initialize", context, data_dict)

    extras = data_dict.get("__extras", {})
    name = secure_filename(data_dict["name"])

    try:
        storage = shared.get_storage(data_dict["storage"])
    except exceptions.UnknownStorageError as err:
        raise tk.ValidationError({"storage": [str(err)]})

    if not storage.supports(Capability.MULTIPART_UPLOAD):
        raise tk.ValidationError({"storage": ["Operation is not supported"]})

    try:
        upload_data = storage.initialize_multipart_upload(name, extras)
    except exceptions.LargeUploadError as err:
        raise tk.ValidationError({"upload": [str(err)]})

    upload = Upload(
        name=name,
        storage=data_dict["storage"],
        upload_data=upload_data,
    )

    context["session"].add(upload)
    if not context.get("defer_commit"):
        context["session"].commit()

    return upload.dictize(context)


@action
@validate(schema.upload_update)
def files_upload_update(context, data_dict):
    # type: (Any, dict[str, Any]) -> dict[str, Any]
    tk.check_access("files_upload_update", context, data_dict)

    extras = data_dict.get("__extras", {})

    data_dict["id"]
    upload = context["session"].get(Upload, data_dict["id"])
    if not upload:
        raise tk.ObjectNotFound("upload")

    storage = shared.get_storage(upload.storage)

    upload.upload_data = storage.update_multipart_upload(upload.upload_data, extras)
    if not context.get("defer_commit"):
        context["session"].commit()

    return upload.dictize(context)


@action
@validate(schema.upload_complete)
def files_upload_complete(context, data_dict):
    # type: (Any, dict[str, Any]) -> dict[str, Any]
    tk.check_access("files_upload_complete", context, data_dict)

    extras = data_dict.get("__extras", {})

    data_dict["id"]
    upload = context["session"].get(Upload, data_dict["id"])
    if not upload:
        raise tk.ObjectNotFound("upload")

    storage = shared.get_storage(upload.storage)

    storage_data = storage.complete_multipart_upload(upload.upload_data, extras)
    fileobj = File(name=upload.name, storage=upload.storage, storage_data=storage_data)

    context["session"].delete(upload)
    context["session"].add(fileobj)
    if not context.get("defer_commit"):
        context["session"].commit()

    return fileobj.dictize(context)
