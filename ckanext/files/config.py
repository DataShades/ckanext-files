"""Configuration readers of the extension.

This module contains functions that simplify accessing configuration option
from the CKAN config file.

It's recommended to use these functions istead of accessing config options by
name, if you want your code to be more compatible with different versions of
the extension.

"""

from collections import defaultdict

import six

import ckan.plugins.toolkit as tk

if six.PY3:
    from typing import Any  # isort: skip # noqa: F401


DEFAULT_STORAGE = "ckanext.files.default_storage"
STORAGE_PREFIX = "ckanext.files.storage."


def default_storage():
    # type: () -> str
    """Default storage used for upload when no explicit storage specified."""

    return tk.config.get(DEFAULT_STORAGE, "default")


def storages():
    # type: () -> dict[str, dict[str, Any]]
    """Mapping of storage names to their settings."""

    storages = defaultdict(dict)  # type: dict[str, dict[str, Any]]
    prefix_len = len(STORAGE_PREFIX)
    for k, v in tk.config.items():
        if not k.startswith(STORAGE_PREFIX):
            continue

        try:
            name, option = k[prefix_len:].split(".", 1)
        except ValueError:
            continue

        storages[name][option] = v
    return storages
