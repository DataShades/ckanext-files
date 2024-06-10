"""Configuration readers of the extension.

This module contains functions that simplify accessing configuration option
from the CKAN config file.

It's recommended to use these functions istead of accessing config options by
name, if you want your code to be more compatible with different versions of
the extension.

"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import ckan.plugins.toolkit as tk

DEFAULT_STORAGE = "ckanext.files.default_storage"
STORAGE_PREFIX = "ckanext.files.storage."
CASCADE_ACCESS = "ckanext.files.owner.cascade_access"
AUTHENTICATED_UPLOADS = "ckanext.files.allow_authenticated_uploads"


def default_storage() -> str:
    """Default storage used for upload when no explicit storage specified."""
    return tk.config[DEFAULT_STORAGE]


def storages() -> dict[str, dict[str, Any]]:
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


def cascade_access() -> list[str]:
    """List of owner types that grant automatic access on owned file."""
    return tk.config[CASCADE_ACCESS]


def authenticated_uploads() -> bool:
    """Any authenticated user can upload files."""

    return tk.config[AUTHENTICATED_UPLOADS]
