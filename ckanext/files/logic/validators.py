import cgi
import mimetypes
from io import BytesIO

import magic
import six
from werkzeug.datastructures import FileStorage

import ckan.plugins.toolkit as tk

from ckanext.files.utils import make_collector

from ckanext.files import types, utils  # isort: skip # noqa: F401

if six.PY3:
    from typing import Any  # isort: skip # noqa: F401

_validators, validator = make_collector()


def get_validators():
    return dict(_validators)


@validator
def files_into_upload(value):
    # type: (Any) -> types.Upload
    """Convert value into werkzeug.FileStorage object"""
    if isinstance(value, FileStorage):
        if not value.content_length:
            value.stream.seek(0, 2)
            value.headers["content-length"] = str(value.stream.tell())
            value.stream.seek(0)
        return value

    if isinstance(value, cgi.FieldStorage):
        if not value.filename or not value.file:
            raise ValueError(value)

        mime, _encoding = mimetypes.guess_type(value.filename)
        if not mime:
            mime = magic.from_buffer(value.file.read(1024), True)
            value.file.seek(0)
        value.file.seek(0, 2)
        size = value.file.tell()
        value.file.seek(0)

        return FileStorage(
            value.file,
            value.filename,
            content_type=mime,
            content_length=size,
        )

    if isinstance(value, six.text_type):
        value = value.encode()

    if isinstance(value, (bytes, bytearray)):
        stream = BytesIO(value)
        mime = magic.from_buffer(stream.read(1024), True)
        stream.seek(0, 2)
        size = stream.tell()
        stream.seek(0)

        return FileStorage(stream, content_type=mime, content_length=size)

    msg = "Unsupported source type: {}".format(type(value))
    raise tk.Invalid(msg)


@validator
def files_parse_filesize(value):
    # type: (Any) -> int
    """Convert human-readable filesize into an integer."""

    if isinstance(value, int):
        return value

    try:
        return utils.parse_filesize(value)
    except ValueError:
        raise tk.Invalid("Wrong filesize string: {}".format(value))  # noqa: B904
