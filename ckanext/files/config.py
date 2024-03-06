from collections import defaultdict

import six

import ckan.plugins.toolkit as tk

if six.PY3:
    from typing import Any  # isort: skip # noqa: F401


DEFAULT_STORAGE = "ckanext.files.default_storage"

STORAGE_PREFIX = "ckanext.files.storage."


def default_storage():
    # type: () -> str
    return tk.config.get(DEFAULT_STORAGE, "default")


def storages():
    # type: () -> dict[str, dict[str, Any]]
    storages = defaultdict(lambda: defaultdict(dict))  # type: dict[str, dict[str, Any]]
    prefix_len = len(STORAGE_PREFIX)
    for k, v in tk.config.items():
        if not k.startswith(STORAGE_PREFIX):
            continue

        try:
            type, option = k[prefix_len:].split(".", 1)
        except ValueError:
            continue

        storages[type][option] = v
    return storages
