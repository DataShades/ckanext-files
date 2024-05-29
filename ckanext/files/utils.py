"""Internal utilities of the extension.

Do not use this module outside of the extension and do not import any other
internal modules except for types and exceptions. Only independent tools are
stored here, to avoid import cycles.

"""

from __future__ import annotations

import contextlib
import mimetypes
import re
import tempfile
from io import BytesIO
from typing import Any, Callable, TypeVar, cast

import magic
import six
from typing_extensions import Generic
from werkzeug.datastructures import FileStorage

from ckanext.files import exceptions, types

T = TypeVar("T")
TC = TypeVar("TC", bound=Callable[..., Any])

RE_FILESIZE = re.compile(r"^(?P<size>\d+(?:\.\d+)?)\s*(?P<unit>\w*)$")

UNITS = cast(
    "dict[str, int]",
    {
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
    },
)


class Registry(Generic[T]):
    """Mutable collection of objects.

    Example:
    >>> col = Registry()
    >>>
    >>> col.register("one", 1)
    >>> assert col.get("one") == 1
    >>>
    >>> col.reset()
    >>> assert col.get("one") is None
    """

    def __init__(self, members: dict[str, T] | None = None) -> None:
        if members is None:
            members = {}
        self.members = members

    def __iter__(self):
        return iter(self.members)

    def __getitem__(self, key: str):
        return self.members[key]

    def reset(self):
        """Remove all members from registry."""

        self.members.clear()

    def register(self, name: str, member: T) -> None:
        """Add a member to registry."""

        self.members[name] = member

    def get(self, name: str) -> T | None:
        """Get an optional member from registry."""

        return self.members.get(name)


def make_collector() -> tuple[dict[str, TC], Callable[[TC], TC]]:
    """Create pair of a dictionary and decorator that appends function to the
    dictionary.

    Example:
    >>> col, add = make_collector()
    >>> assert col == {}
    >>>
    >>> @add
    >>> def hello():
    >>>     return "world"
    >>>
    >>> assert col == {"hello": hello}
    """

    collection: dict[str, TC] = {}

    def collector(fn: TC) -> TC:
        """Decorator that appends functions to the collection."""

        collection[fn.__name__] = fn
        return fn

    return collection, collector


def ensure_size(upload: types.Upload, max_size: int) -> int:
    """Return filesize or rise an exception if it exceedes max_size."""

    filesize = upload.content_length
    if not filesize:
        upload.stream.seek(0, 2)
        filesize = upload.stream.tell()
        upload.stream.seek(0)

    if filesize > max_size:
        raise exceptions.LargeUploadError(filesize, max_size)

    return filesize


def combine_capabilities(
    *capabilities: types.CapabilityCluster | types.CapabilityUnit,
) -> types.CapabilityCluster:
    """Combine multiple capabilities.

    Example:
    >>> cluster = combine_capabilities(Capability.CREATE, Capability.REMOVE)
    """

    result = 0
    for capability in capabilities:
        result |= capability

    return types.CapabilityCluster(result)


def exclude_capabilities(
    capabilities: types.CapabilityCluster,
    *exclude: types.CapabilityCluster | types.CapabilityUnit,
) -> types.CapabilityCluster:
    """Remove capabilities from the cluster

    Example:
    >>> cluster = exclude_capabilities(cluster, Capability.REMOVE)
    """

    for capability in exclude:
        capabilities = types.CapabilityCluster(capabilities & ~capability)

    return capabilities


def parse_filesize(value: str) -> int:
    """Transform human-readable filesize into an integer.

    Example:
    >>> size = parse_filesize("10GiB")
    >>> assert size == 10_737_418_240
    """
    result = RE_FILESIZE.match(value.strip())
    if not result:
        raise ValueError(value)
    size, unit = result.groups()

    multiplier = UNITS.get(unit.lower())
    if not multiplier:
        raise ValueError(value)

    return int(float(size) * multiplier)


def make_upload(
    value: (
        FileStorage
        | tempfile.SpooledTemporaryFile[Any]
        | str
        | bytes
        | bytearray
        | BytesIO
        | Any
    ),
) -> types.Upload:
    """Convert value into werkzeug.FileStorage object"""
    with contextlib.suppress(ImportError):
        import cgi

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

    if isinstance(value, FileStorage):
        if not value.content_length:
            value.stream.seek(0, 2)
            value.headers["content-length"] = str(value.stream.tell())
            value.stream.seek(0)
        return value

    if isinstance(value, tempfile.SpooledTemporaryFile):
        mime = magic.from_buffer(value.read(1024), True)
        value.seek(0, 2)
        size = value.tell()
        value.seek(0)

        return FileStorage(value, "", content_type=mime, content_length=size)

    if isinstance(value, six.text_type):
        value = value.encode()

    if isinstance(value, (bytes, bytearray)):
        value = BytesIO(value)

    if isinstance(value, BytesIO):
        mime = magic.from_buffer(value.read(1024), True)
        value.seek(0, 2)
        size = value.tell()
        value.seek(0)

        return FileStorage(value, content_type=mime, content_length=size)

    raise TypeError(type(value))
