# -*- coding: utf-8 -*-

import six
from ckanext.files.storage import Storage
from ckanext.files.exceptions import UnknownStorageError
from ckanext.files.utils import Registry, adapters, combine_capabilities

if six.PY3:  # pragma: no cover
    from typing import Any


__all__ = [
    "get_storage",
    "UnknownStorageError",
    "Storage",
    "adapters",
    "combine_capabilities",
]

storages = Registry({})


def get_storage(name):
    # type: (str) -> Storage
    storage = storages.get(name)

    if not storage:
        raise UnknownStorageError(name)

    return storage
