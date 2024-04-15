import six

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
    try:
        return utils.make_upload(value)

    except TypeError as err:
        msg = "Unsupported source type: {}".format(err)
        raise tk.Invalid(msg)  # noqa: B904

    except ValueError as err:
        msg = "Wrong file: {}".format(err)
        raise tk.Invalid(msg)  # noqa: B904


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
