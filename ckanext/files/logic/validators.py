from __future__ import annotations

from typing import Any

import ckan.plugins.toolkit as tk

from ckanext.files import types, utils


def files_into_upload(value: Any) -> types.Upload:
    """Convert value into werkzeug.FileStorage object"""
    try:
        return utils.make_upload(value)

    except TypeError as err:
        msg = "Unsupported source type: {}".format(err)
        raise tk.Invalid(msg)  # noqa: B904

    except ValueError as err:
        msg = "Wrong file: {}".format(err)
        raise tk.Invalid(msg)  # noqa: B904


def files_parse_filesize(value: Any) -> int:
    """Convert human-readable filesize into an integer."""

    if isinstance(value, int):
        return value

    try:
        return utils.parse_filesize(value)
    except ValueError:
        raise tk.Invalid("Wrong filesize string: {}".format(value))  # noqa: B904
