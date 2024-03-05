import cgi
import mimetypes
from io import BytesIO

import magic
import six
from werkzeug.datastructures import FileStorage

import ckan.plugins.toolkit as tk

from ckanext.files.utils import make_collector

if six.PY3:
    from typing import Any  # isort: skip # noqa: F401

_validators, validator = make_collector()


def get_validators():
    return dict(_validators)


@validator
def files_into_upload(value):
    # type: (Any) -> FileStorage
    """Try converting value into werkzeug.FileStorage object"""
    if isinstance(value, FileStorage):
        if not value.content_length:
            value.headers["content-length"] = str(value.stream.seek(0, 2))
            value.stream.seek(0)
        return value

    if isinstance(value, cgi.FieldStorage):
        if not value.filename or not value.file:
            raise ValueError(value)

        mime, _encoding = mimetypes.guess_type(value.filename)
        if not mime:
            mime = magic.from_buffer(value.file.read(1024), True)
            value.file.seek(0)
        size = value.file.seek(0, 2)
        value.file.seek(0)

        return FileStorage(
            value.file,
            value.filename,
            content_type=mime,
            content_length=size,
        )

    if isinstance(value, str):
        value = value.encode()

    if isinstance(value, bytes):
        stream = BytesIO(value)
        mime = magic.from_buffer(stream.read(1024), True)
        size = stream.seek(0, 2)
        stream.seek(0)

        return FileStorage(stream, content_type=mime, content_length=size)

    msg = "Unsupported source type: {}".format(type(value))
    raise tk.Invalid(msg)
