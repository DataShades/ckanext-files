"""Internal utilities of the extension.

Do not use this module outside of the extension and do not import any other
internal module except for config and exceptions. Only independent
tools are stored here, to avoid import cycles.

"""

from __future__ import annotations

import contextlib
import dataclasses
import enum
import hashlib
import logging
import mimetypes
import re
import tempfile
from io import BufferedReader, BytesIO, TextIOWrapper
from typing import IO, Any, BinaryIO, Callable, Generic, Iterable, TypeVar, cast

import jwt
import magic
from sqlalchemy.orm import Mapper
from werkzeug.datastructures import FileStorage

import ckan.plugins.toolkit as tk
from ckan import model
from ckan.lib.api_token import _get_algorithm, _get_secret  # type: ignore

log = logging.getLogger(__name__)

T = TypeVar("T")

RE_FILESIZE = re.compile(r"^(?P<size>\d+(?:\.\d+)?)\s*(?P<unit>\w*)$")
CHUNK_SIZE = 16 * 1024
SAMPLE_SIZE = 1024 * 2
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
        "p": 10**15,
        "tb": 10**12,
        "kib": 2**10,
        "mib": 2**20,
        "gib": 2**30,
        "tib": 2**40,
        "pib": 2**50,
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

    def read(self):
        return b"".join(self)

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


owner_getters = Registry[Callable[[str], Any]]({})


def get_owner(owner_type: str, owner_id: str):
    if getter := owner_getters.get(owner_type):
        return getter(owner_id)

    owner_model = "group" if owner_type == "organization" else owner_type
    mappers: Iterable[Mapper]
    if tk.check_ckan_version("2.11"):
        mappers = model.registry.mappers
    else:
        mappers = cast(
            Iterable[Mapper],
            tk.BaseModel._sa_registry.mappers
            | model.User._sa_class_manager.registry.mappers,  # type: ignore
        )

    for mapper in mappers:
        cls = mapper.class_
        table = getattr(cls, "__table__", None)
        if table is None:
            table = getattr(mapper, "local_table", None)

        if table is not None and table.name == owner_model:
            return model.Session.get(cls, owner_id)

    log.warning("Unknown owner type %s with ID %s", owner_type, owner_id)
    return None


def is_supported_type(content_type: str, supported: Iterable[str]) -> str | None:
    """Return content type if it matches supported types."""

    maintype, subtype = content_type.split("/")
    for st in supported:
        if st in [content_type, maintype, subtype]:
            return content_type


class Capability(enum.Flag):
    """Enumeration of operations supported by the storage.

    Example:
    >>> read_and_write = Capability.STREAM | Capability.CREATE
    >>> if storage.supports(read_and_write)
    >>>     ...
    """

    NONE = 0

    # create a file as an atomic object
    CREATE = enum.auto()
    # return file content as stream of bytes
    STREAM = enum.auto()
    # make a copy of the file inside the same storage
    COPY = enum.auto()
    # remove file from the storage
    REMOVE = enum.auto()
    # create file in 3 stages: initialize, upload(repeatable), complete
    MULTIPART = enum.auto()
    # move file to a different location inside the same storage
    MOVE = enum.auto()
    # check if file exists
    EXISTS = enum.auto()
    # iterate over all files in the storage
    SCAN = enum.auto()
    # add content to the existing file
    APPEND = enum.auto()
    # combine multiple files into a new one in the same storage
    COMPOSE = enum.auto()
    # return specific range of bytes from the file
    RANGE = enum.auto()
    # return file details from the storage, as if file was uploaded just now
    ANALYZE = enum.auto()
    # make permanent download link for private file
    PERMANENT_LINK = enum.auto()
    # make expiring download link for private file
    TEMPORAL_LINK = enum.auto()
    # make one-time download link for private file
    ONE_TIME_LINK = enum.auto()
    # make permanent public(anonymously accessible) link
    PUBLIC_LINK = enum.auto()

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
    threshold = 1024
    while value > threshold:
        iteration += 1
        value /= threshold

    value = int(value * 100) / 100
    return f"{value:.2f}{suffixes[iteration]}"


def make_upload(
    value: (
        FileStorage
        | Upload
        | tempfile.SpooledTemporaryFile[Any]
        | TextIOWrapper
        | bytes
        | bytearray
        | BinaryIO
    ),
) -> Upload:
    """Convert value into Upload object

    Use this function for simple and reliable initialization of Upload
    object. Avoid creating Upload manually, unless you are 100% sure you can
    provide correct MIMEtype, size and stream.

    Example:
    >>> storage.upload("file.txt", make_upload(b"hello world"))

    """
    if isinstance(value, Upload):
        return value

    with contextlib.suppress(ImportError):  # pragma: no cover
        import cgi

        if isinstance(value, cgi.FieldStorage):
            if not value.filename or not value.file:
                raise ValueError(value)

            mime, _encoding = mimetypes.guess_type(value.filename)
            if not mime:
                mime = magic.from_buffer(value.file.read(SAMPLE_SIZE), True)
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

    if isinstance(value, (bytes, bytearray)):
        value = BytesIO(value)

    if isinstance(value, TextIOWrapper):
        value = value.buffer

    if isinstance(value, (BytesIO, BufferedReader)):
        mime = magic.from_buffer(value.read(SAMPLE_SIZE), True)
        value.seek(0, 2)
        size = value.tell()
        value.seek(0)

        return Upload(value, getattr(value, "name", ""), size, mime)

    raise TypeError(type(value))


def _file_storage_as_upload(value: FileStorage):
    name: str = value.filename or value.name or ""

    if value.content_length:
        size = value.content_length
    else:
        value.stream.seek(0, 2)
        size = value.stream.tell()
        value.stream.seek(0)

    mime = magic.from_buffer(value.stream.read(SAMPLE_SIZE), True)
    value.stream.seek(0)

    return Upload(value.stream, name, size, mime)


def _tempfile_as_upload(value: tempfile.SpooledTemporaryFile[bytes]):
    mime = magic.from_buffer(value.read(SAMPLE_SIZE), True)
    value.seek(0, 2)
    size = value.tell()
    value.seek(0)

    return Upload(value, value.name or "", size, mime)


def encode_token(data: dict[str, Any]) -> str:
    return jwt.encode(data, _get_secret(encode=True), algorithm=_get_algorithm())


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, _get_secret(encode=False), algorithms=[_get_algorithm()])
