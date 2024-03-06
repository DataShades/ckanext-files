"""Internal utilities of the extension.

Do not use this module outside of the extension and do not import any other
internal modules except for types and exceptions. Only independent tools are
stored here, to avoid import cycles.

"""

import re

import six

from ckanext.files import exceptions

from ckanext.files import types  # isort: skip # noqa: 401

if six.PY3:
    from typing import TypeVar

    from typing import Callable, Any  # isort: skip # noqa: F401

    T = TypeVar("T")


RE_FILESIZE = re.compile(r"^(?P<size>\d+(?:\.\d+)?)\s*(?P<unit>\w*)$")
UNITS = {
    "": 1,
    "b": 1,
    "k": 10**3,
    "kb": 10**3,
    "m": 10**6,
    "mb": 10**6,
    "g": 10**9,
    "gb": 10**9,
    "t": 10**12,
    "tb": 10**12,
    "kib": 2**10,
    "mib": 2**20,
    "gib": 2**30,
    "tib": 2**40,
}  # type: dict[str, int]


class Registry(object):
    def __init__(self, members=None):
        # type: (dict[str, Any] | None) -> None
        if members is None:
            members = {}
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


def ensure_size(upload, max_size):
    # type: (types.Upload, int) -> int

    filesize = upload.content_length
    if not filesize:
        filesize = upload.stream.seek(0, 2)
        upload.stream.seek(0)

    if filesize > max_size:
        raise exceptions.LargeUploadError(filesize, max_size)

    return filesize


def combine_capabilities(*capabilities):
    # type: (*types.CapabilityCluster | types.CapabilityUnit) -> types.CapabilityCluster
    result = 0
    for capability in capabilities:
        result |= capability

    return types.CapabilityCluster(result)


def exclude_capabilities(capabilities, *exclude):
    # type: (types.CapabilityCluster, *types.CapabilityCluster | types.CapabilityUnit) -> types.CapabilityCluster
    for capability in exclude:
        capabilities = types.CapabilityCluster(capabilities & ~capability)

    return capabilities


def parse_filesize(value):
    # type: (str) -> int
    result = RE_FILESIZE.match(value.strip())
    if not result:
        raise ValueError(value)
    size, unit = result.groups()

    multiplier = UNITS.get(unit.lower())
    if not multiplier:
        raise ValueError(value)

    return int(float(size) * multiplier)
