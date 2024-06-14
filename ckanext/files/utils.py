"""Internal utilities of the extension.

Do not use this module outside of the extension and do not import any other
internal module except for config and exceptions. Only independent
tools are stored here, to avoid import cycles.

"""

from __future__ import annotations

import abc
import contextlib
import contextvars
import dataclasses
import enum
import functools
import hashlib
import logging
import mimetypes
import re
import tempfile
from io import BufferedReader, BytesIO
from typing import IO, Any, Callable, Generic, Iterable, Literal, TypeVar, cast

import jwt
import magic
from sqlalchemy.orm import Mapper
from werkzeug.datastructures import FileStorage

import ckan.plugins.toolkit as tk
from ckan import model
from ckan.lib.api_token import _get_algorithm, _get_secret  # type: ignore
from ckan.types import FlattenKey

from ckanext.files import exceptions

log = logging.getLogger(__name__)

_task_queue: contextvars.ContextVar[list[Task] | None] = contextvars.ContextVar(
    "transfer_queue",
    default=None,
)
T = TypeVar("T")
AuthOperation = Literal["show", "update", "delete", "file_transfer"]
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
    """Return content type of upload or rise an exception if type is not supported"""

    maintype, subtype = content_type.split("/")
    for st in supported:
        if st in [content_type, maintype, subtype]:
            return content_type


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
    # make permanent public(anonymously accessible) link
    PUBLIC_LINK = enum.auto()

    @staticmethod
    def combine(*capabilities: Capability):
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
        | BufferedReader
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

    if isinstance(value, (BytesIO, BufferedReader)):
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


def encode_token(data: dict[str, Any]) -> str:
    return jwt.encode(data, _get_secret(encode=True), algorithm=_get_algorithm())


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, _get_secret(encode=False), algorithms=[_get_algorithm()])


class TaskQueue:
    queue: list[Any]
    token: contextvars.Token[Any] | None

    def __len__(self):
        return len(self.queue)

    def __init__(self):
        self.queue = []
        self.token = None

    def __enter__(self):
        self.token = _task_queue.set(self.queue)
        return self.queue

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any):
        if self.token:
            _task_queue.reset(self.token)

    @classmethod
    def add_task(cls, task: Task):
        queue = _task_queue.get()
        if queue is None:
            raise exceptions.OutOfQueueError
        queue.append(task)

    def process(self, result: dict[str, Any]):
        while self.queue:
            task = self.queue.pop(0)
            task.run(result)


class Task(abc.ABC):
    @staticmethod
    def extract(source: dict[str, Any], path: FlattenKey):
        for step in path:
            source = source[step]

        return source

    @abc.abstractmethod
    def run(self, result: dict[str, Any]): ...


@dataclasses.dataclass
class OwnershipTransferTask(Task):
    file_id: str
    owner_type: str
    id_path: FlattenKey

    def run(self, result: dict[str, Any]):
        tk.get_action("files_transfer_ownership")(
            {"ignore_auth": True},
            {
                "id": self.file_id,
                "owner_type": self.owner_type,
                "owner_id": self.extract(result, self.id_path),
                "force": True,
                "pin": True,
            },
        )


@dataclasses.dataclass
class UploadAndAttachTask(Task):
    storage: str
    upload: Upload
    owner_type: str
    id_path: FlattenKey

    attach_as: Literal["id", "public_url"] | None
    action: str | None = None
    destination_field: str | None = None

    def run(self, result: dict[str, Any]):
        from ckanext.files import shared

        info = tk.get_action("files_file_create")(
            {"ignore_auth": True},
            {"upload": self.upload, "storage": self.storage},
        )

        info = tk.get_action("files_transfer_ownership")(
            {"ignore_auth": True},
            {
                "id": info["id"],
                "owner_type": self.owner_type,
                "owner_id": self.extract(result, self.id_path),
                "force": True,
                "pin": True,
            },
        )

        if self.attach_as and self.action and self.destination_field:
            if self.attach_as:
                storage = shared.get_storage(self.storage)
                value = storage.public_link(shared.FileData.from_dict(info))
            else:
                value = info["id"]

            user = tk.get_action("get_site_user")({"ignore_auth": True}, {})
            tk.get_action(self.action)(
                {"ignore_auth": True, "user": user["name"]},
                {"id": info["owner_id"], self.destination_field: value},
            )


def action_with_task_queue(action: Any, name: str | None = None):
    @functools.wraps(action)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        queue = TaskQueue()
        with queue:
            result = action(*args, *kwargs)
            queue.process(result)

        return result

    if name:
        wrapper.__name__ = name
    return wrapper
