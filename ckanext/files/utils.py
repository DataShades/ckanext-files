"""Internal utilities of the extension.

Do not use this module outside of the extension and do not import any other
internal module except for types, config, interfaces and exceptions. Only independent
tools are stored here, to avoid import cycles.

"""

from __future__ import annotations

import contextlib
import dataclasses
import enum
import hashlib
import mimetypes
import re
import tempfile
from io import BytesIO
from typing import IO, Any, Generic, TypeVar, cast

import magic
from werkzeug.datastructures import FileStorage

import ckan.plugins as p
import ckan.plugins.toolkit as tk
from ckan import model
from ckan.types import Context

from ckanext.files import config, exceptions, interfaces, types

T = TypeVar("T")

RE_FILESIZE = re.compile(r"^(?P<size>\d+(?:\.\d+)?)\s*(?P<unit>\w*)$")
CHUNK_SIZE = 16 * 1024
CHECKSUM_ALGORITHM = "md5"

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


@dataclasses.dataclass
class Upload:
    stream: IO[bytes]
    filename: str
    size: int
    content_type: str

    def hashing_reader(self, **kwargs: Any) -> HashingReader:
        return HashingReader(self.stream, **kwargs)


class HashingReader:
    """IO stream wrapper that computes content hash while stream is consumed.

    Example:

    >>> reader = HashingReader(readable_stream)
    >>> for chunk in reader:
    >>>     ...
    >>> print(f"Hash: {reader.get_hash()}")

    """

    def __init__(
        self,
        stream: IO[bytes],
        chunk_size: int = CHUNK_SIZE,
        algorithm: str = CHECKSUM_ALGORITHM,
    ) -> None:
        self.stream = stream
        self.chunk_size = chunk_size
        self.algorithm = algorithm
        self.hashsum = hashlib.new(algorithm)
        self.position = 0

    def __iter__(self):
        return self

    def __next__(self):
        chunk = self.stream.read(self.chunk_size)
        if not chunk:
            raise StopIteration

        self.position += len(chunk)
        self.hashsum.update(chunk)
        return chunk

    next = __next__

    def reset(self):
        """Rewind underlying stream and reset hash to initial state."""
        self.position = 0
        self.hashsum = hashlib.new(self.algorithm)
        self.stream.seek(0)

    def get_hash(self):
        """Get content hash as a string."""
        return self.hashsum.hexdigest()

    def exhaust(self):
        """Exhaust internal stream to compute final version of content hash."""

        for _ in self:
            pass


class Capability(enum.Flag):
    """Enumeration of operations supported by the storage.

    Do not assume internal implementation of this type. Use Storage.supports,
    Capability.combine, and Capability.exclude to check and modify capabilities
    of the storage.

    Example:
    >>> read_and_write = Capability.combine(
    >>>     Capability.STREAM, Capability.CREATE,
    >>> )
    >>> if storage.supports(read_and_write)
    >>>     ...
    """

    NONE = 0

    # create a file as an atomic object
    CREATE = enum.auto()
    # return file content as stream of bytes
    STREAM = enum.auto()
    # make a copy of the file inside the storage
    COPY = enum.auto()
    # remove file from the storage
    REMOVE = enum.auto()
    # create file in 3 stages: initialize, upload(repeatable), complete
    MULTIPART = enum.auto()
    # move file to a different location inside the storage
    MOVE = enum.auto()
    # check if file exists
    EXISTS = enum.auto()
    # iterate over all files in storage
    SCAN = enum.auto()
    # add content to the existing file
    APPEND = enum.auto()
    # combine multiple files into a new one
    COMPOSE = enum.auto()
    # return specific range of file bytes
    RANGE = enum.auto()
    # return file details from the storage, as if file was uploaded just now
    ANALYZE = enum.auto()
    # make permanent download link
    PERMANENT_LINK = enum.auto()
    # make expiring download link
    TEMPORAL_LINK = enum.auto()
    # make one-time download link
    ONE_TIME_LINK = enum.auto()

    @classmethod
    def combine(cls, *capabilities: Capability):
        """Combine multiple capabilities.

        Example:
        >>> cluster = Capability.CREATE.combine(Capability.REMOVE)
        """
        result = Capability.NONE
        for capability in capabilities:
            result |= capability
        return result

    def exclude(self, *capabilities: Capability):
        """Remove capabilities from the cluster

        Example:
        >>> cluster = cluster.exclude(Capability.REMOVE)
        """

        result = Capability(self)
        for capability in capabilities:
            result = result & ~capability
        return result

    def can(self, operation: Capability) -> bool:
        return (self & operation) == operation


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


def ensure_size(upload: Upload, max_size: int) -> int:
    """Return filesize or rise an exception if it exceedes max_size."""

    if upload.size > max_size:
        raise exceptions.LargeUploadError(upload.size, max_size)

    return upload.size


def ensure_type(upload: Upload, types: list[str]) -> str:
    """Return content type of upload or rise an exception if type is not supported"""

    maintype, subtype = upload.content_type.split("/")
    for option in types:
        if option in [upload.content_type, maintype, subtype]:
            return upload.content_type

    raise exceptions.WrongUploadTypeError(upload.content_type)


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


def humanize_filesize(value: int | float) -> str:
    """Transform an integer into human-readable filesize.

    Example:
    >>> size = humanize_filesize(10_737_418_240)
    >>> assert size == "10GiB"
    >>> size = humanize_filesize(10_418_240)
    >>> assert size == "9.9MiB"
    """
    suffixes = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]
    iteration = 0
    while value > 1024:
        iteration += 1
        value /= 1024

    value = int(value * 100) / 100
    return f"{value:.2g}{suffixes[iteration]}"


def make_upload(
    value: (
        FileStorage
        | Upload
        | tempfile.SpooledTemporaryFile[Any]
        | str
        | bytes
        | bytearray
        | BytesIO
        | Any
    ),
) -> Upload:
    """Convert value into Upload object"""
    if isinstance(value, Upload):
        return value

    with contextlib.suppress(ImportError):  # pragma: no cover
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

            return Upload(
                value.file,
                value.filename,
                size,
                mime,
            )

    if isinstance(value, FileStorage):
        return _file_storage_as_upload(value)

    if isinstance(value, tempfile.SpooledTemporaryFile):
        return _tempfile_as_upload(value)

    if isinstance(value, str):
        value = value.encode()

    if isinstance(value, (bytes, bytearray)):
        value = BytesIO(value)

    if isinstance(value, BytesIO):
        mime = magic.from_buffer(value.read(1024), True)
        value.seek(0, 2)
        size = value.tell()
        value.seek(0)

        return Upload(value, "", size, mime)

    raise TypeError(type(value))


def _file_storage_as_upload(value: FileStorage):
    name: str = value.filename or value.name or ""

    if value.content_length:
        size = value.content_length
    else:
        value.stream.seek(0, 2)
        size = value.stream.tell()
        value.stream.seek(0)

    mime, _encoding = mimetypes.guess_type(name)
    if not mime:
        mime = magic.from_buffer(value.stream.read(1024), True)
        value.stream.seek(0)

    return Upload(value.stream, name, size, mime)


def _tempfile_as_upload(value: tempfile.SpooledTemporaryFile[bytes]):
    mime = magic.from_buffer(value.read(1024), True)
    value.seek(0, 2)
    size = value.tell()
    value.seek(0)

    return Upload(value, value.name or "", size, mime)


def materialize_owner(owner_type: str, owner_id: str) -> Any:
    """Transform owner details into owner entity."""

    not_exist = object()

    for plugin in p.PluginImplementations(interfaces.IFiles):
        owner = plugin.files_materialize_owner(owner_type, owner_id, not_exist)
        if owner is not_exist:
            return None

        if owner is not None:
            return owner

    for mapper in model.registry.mappers:
        cls = mapper.class_
        if hasattr(cls, "__table__") and cls.__table__.name == owner_type:
            return model.Session.get(cls, owner_id)

    raise TypeError(owner_type)


def is_allowed(context: Context, file: Any, operation: types.AuthOperation) -> Any:
    """Decide if user is allowed to perform operation on file."""
    info = file.owner_info

    if info and info.owner_type in config.cascade_access():
        try:
            tk.check_access(
                f"{info.owner_type}_{operation}",
                context,
                {"id": info.owner_id},
            )

        except tk.NotAuthorized:
            return False

        except ValueError:
            pass

    for plugin in p.PluginImplementations(interfaces.IFiles):
        result = plugin.files_is_allowed(context, file, operation)
        if result is not None:
            return result
