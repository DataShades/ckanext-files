from __future__ import annotations
import os
from typing import Optional
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

    uploader = files_uploader(data_dict["kind"])
    uploader.update_data_dict(data_dict, "path", "upload", None)

    max_size = tk.asint(tk.config.get(CONFIG_SIZE.format(kind=data_dict["kind"]), DEFAULT_SIZE))
    uploader.upload(max_size)

    # TODO: try not to rely on hardcoded segments
    data_dict["path"] = os.path.relpath(uploader.filepath, os.path.join(get_storage_path(), "storage"))

    file = File(**data_dict)
    context["session"].add(file)
    context["session"].commit()
    return file.dictize(context)


@action
@validate(schema.file_update)
def file_update(context, data_dict):
    tk.check_access("files_file_delete", context, data_dict)
    file = (
        context["session"]
        .query(File)
        .filter_by(id=data_dict["id"])
        .one_or_none()
    )
    if not file:
        raise tk.ObjectNotFound("File not found")

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
