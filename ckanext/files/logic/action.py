from __future__ import annotations
import os
from typing import Any, Optional
import ckan.plugins.toolkit as tk
from ckan.logic import validate
from ckan.lib.uploader import get_uploader, get_storage_path

from ckanext.toolbelt.decorators import Collector

from ckanext.files.model import File
from . import schema

action, get_actions = Collector("files").split()

CONFIG_SIZE = "ckanext.files.kind.{kind}.max_size"
DEFAULT_SIZE = 2


def files_uploader(kind: str, old_filename: Optional[str] = None):
    return get_uploader(kind, old_filename)


@action
@validate(schema.file_create)
def file_create(context, data_dict):
    tk.check_access("files_file_create", context, data_dict)

    _upload(data_dict, data_dict["kind"])

    file = File(**data_dict)
    context["session"].add(file)
    context["session"].commit()
    return file.dictize(context)


def _upload(data_dict: dict[str, Any], kind: str):
    uploader = files_uploader(kind)
    uploader.update_data_dict(data_dict, "path", "upload", None)

    max_size = tk.asint(
        tk.config.get(CONFIG_SIZE.format(kind=kind), DEFAULT_SIZE)
    )
    uploader.upload(max_size)

    # TODO: try not to rely on hardcoded segments
    data_dict["path"] = os.path.relpath(
        uploader.filepath, os.path.join(get_storage_path(), "storage")
    )


@action
@validate(schema.file_update)
def file_update(context, data_dict):
    tk.check_access("files_file_delete", context, data_dict)
    file: File = (
        context["session"]
        .query(File)
        .filter_by(id=data_dict["id"])
        .one_or_none()
    )
    if not file:
        raise tk.ObjectNotFound("File not found")

    # TODO: remove old file
    if "upload" in data_dict:
        _upload(data_dict, file.kind)

    for attr, value in data_dict.items():
        setattr(file, attr, value)
    context["session"].commit()
    return file.dictize(context)


@action
def file_delete(context, data_dict):
    id_ = tk.get_or_bust(data_dict, "id")
    tk.check_access("files_file_delete", context, data_dict)
    file = context["session"].query(File).filter_by(id=id_).one_or_none()
    if not file:
        raise tk.ObjectNotFound("File not found")

    context["session"].delete(file)
    context["session"].commit()

    _remove_file_from_filesystem(file.path)

    return True


@action
def file_show(context, data_dict):
    id_ = tk.get_or_bust(data_dict, "id")
    tk.check_access("files_file_show", context, data_dict)

    query = context["session"].query(File)
    file = query.filter_by(id=id_).one_or_none()
    if not file:
        file = query.filter_by(name=id_).one_or_none()
    if not file:
        raise tk.ObjectNotFound("File not found")

    return file.dictize(context)


def _remove_file_from_filesystem(file_path: str) -> bool:
    """Remove a file from the file system"""
    storage_path = get_storage_path()
    file_path = os.path.join(storage_path, 'storage', file_path)

    if not os.path.exists(file_path):
        # TODO: What are we going to do then? Probably, skip silently
        return True

    try:
        os.remove(file_path)
    except OSError:
        # TODO: in future, we are going to rewrite code a bit, so we could
        # track files that are hanging by themselves and clear em
        return False

    return True
