# -*- coding: utf-8 -*-

import six
from ckanext.files import exceptions
from werkzeug.datastructures import FileStorage

if six.PY3:  # pragma: no cover
    from typing import Any, Callable, TypeVar, TYPE_CHECKING, Iterable

    T = TypeVar("T")
    if TYPE_CHECKING:
        from ckanext.files.storage import Storage
        from ckanext.files.storage.base import CapabilityCluster, CapabilityUnit


class Registry(object):
    def __init__(self, members):
        # type: (dict[str, Any]) -> None
        self.members = members

    def reset(self):
        self.members.clear()

    def register(self, name, member):
        # type: (str, Any) -> None
        self.members[name] = member

    def get(self, name):
        # type: (str) -> Any | None
        return self.members.get(name)


def make_collector():
    # type: () -> tuple[dict[str, Any], Callable[[Any], Any]]
    collection = {}  # type: dict[str, Any]

    def collector(fn):
        # type: (T) -> T
        collection[fn.__name__] = fn
        return fn

    return collection, collector


adapters = Registry({})


def storage_from_settings(settings):
    # type: (dict[str, Any]) -> Storage

    adapter_type = settings.pop("type", None)
    adapter = adapters.get(adapter_type)  # type: type[Storage] | None
    if not adapter:
        raise exceptions.UnknownAdapterError(adapter_type)

    try:
        return adapter(**settings)
    except TypeError as e:
        raise exceptions.InvalidAdapterConfigurationError(adapter, str(e))


def ensure_size(upload, max_size):
    # type: (FileStorage, int) -> int

    filesize = upload.content_length
    if not filesize:
        filesize = upload.stream.seek(0, 2)
        upload.stream.seek(0)

    if filesize > max_size:
        raise exceptions.LargeUploadError(filesize, max_size)

    return filesize


def combine_capabilities(*capabilities):
    # type: (*CapabilityCluster | CapabilityUnit) -> CapabilityCluster
    result = 0
    for capability in capabilities:
        result |= capability

    return result


def exclude_capabilities(capabilities, *exclude):
    # type: (CapabilityCluster, *CapabilityCluster | CapabilityUnit) -> CapabilityCluster
    for capability in exclude:
        capabilities &= ~capability

    return capabilities
