"""Base abstract functionality of the extentsion.

All classes required for specific storage implementations are defined
here. Some utilities, like `make_storage` are also added to this module instead
of `utils` to avoid import cycles.

This module relies only on types, exceptions and utils to prevent import
cycles.

"""

from __future__ import annotations

import abc
import copy
import dataclasses
import os
import uuid
from datetime import datetime
from typing import IO, Any, Generic, Iterable, Literal

import pytz

from ckan.config.declaration import Declaration, Key

from ckanext.files import config, exceptions, model, utils
from ckanext.files.types import TFileModel

adapters: utils.Registry[type[Storage]] = utils.Registry({})
storages: utils.Registry[Storage] = utils.Registry({})


@dataclasses.dataclass
class BaseData(Generic[TFileModel]):
    location: str
    size: int = 0
    content_type: str = ""
    hash: str = ""
    storage_data: dict[str, Any] = dataclasses.field(default_factory=dict)

    @classmethod
    def from_dict(cls, record: dict[str, Any]):
        return cls(
            record["location"],
            record["size"],
            record["content_type"],
            record["hash"],
            copy.deepcopy(record["storage_data"]),
        )

    @classmethod
    def from_model(cls, record: TFileModel):
        return cls(
            record.location,
            record.size,
            record.content_type,
            record.hash,
            copy.deepcopy(record.storage_data),
        )

    def into_model(self, record: TFileModel):
        record.location = self.location
        record.size = self.size
        record.content_type = self.content_type
        record.hash = self.hash
        record.storage_data = copy.deepcopy(self.storage_data)
        return record


@dataclasses.dataclass
class FileData(BaseData[model.File]):
    content_type: str = "application/octet-stream"


@dataclasses.dataclass
class MultipartData(BaseData[model.Multipart]):
    location: str = ""


def make_storage(name: str, settings: dict[str, Any]) -> Storage:
    """Initialize storage instance with sppeecified settings.

    Storage adapter is defined by `type` key of the settings. All other
    settings depend on the specific adapter.

    Example:
    >>> storage = make_storage("memo", {"type": "files:redis"})
    """

    adapter_type = settings.pop("type", None)
    adapter = adapters.get(adapter_type)
    if not adapter:
        raise exceptions.UnknownAdapterError(adapter_type)

    settings.setdefault("name", name)
    return adapter(**settings)


def get_storage(name: str | None = None) -> Storage:
    """Return existing storage instance.

    Storages are initialized when plugin is loaded. As result, this function
    always returns the same storage object for the given name.

    If no name specified, default storage is returned.

    Example:
    >>> default_storage = get_storage()
    >>> storage = get_storage("storage name")

    """

    if name is None:
        name = config.default_storage()

    storage = storages.get(name)

    if not storage:
        raise exceptions.UnknownStorageError(name)

    return storage


class OptionChecker(object):
    """Mixin for standard access to required settings.

    Example:
    >>> value = storage.ensure_option({...}, "option_name")

    """

    @classmethod
    def ensure_option(cls, settings: dict[str, Any], option: str) -> Any:
        """Return value of the option or rise an exception."""

        if option not in settings:
            raise exceptions.MissingStorageConfigurationError(cls, option)
        return settings[option]


class StorageService(OptionChecker):
    """Base class for services used by storage.

    StorageService.capabilities reflect all operations provided by the
    service. StorageService.required_options list all options that are
    essential for the service. If any of this options is missing from the
    storage, service raises an error during storage initialization stage.

    >>> class Uploader(StorageService):
    >>>     capabilities = Capability.combine(Capability.CREATE)
    >>>     required_options = ["allowed_mimetypes"]

    """

    required_options: list[str] = []
    capabilities = utils.Capability.NONE

    # @property
    # def storage(self):
    #     return self._storage

    def __init__(self, storage: Storage):
        self.storage = storage
        self.ensure_settings()

    def ensure_settings(self):
        for option in self.required_options:
            self.ensure_option(self.storage.settings, option)


class Uploader(StorageService):
    """Service responsible for writing data into a storage."""

    def upload(
        self,
        location: str,
        upload: utils.Upload,
        extras: dict[str, Any],
    ) -> FileData:
        """Upload file using single stream."""

        raise NotImplementedError

    def multipart_start(
        self,
        location: str,
        extras: dict[str, Any],
    ) -> MultipartData:
        """Prepare everything for multipart(resumable) upload."""

        raise NotImplementedError

    # TODO: rename to refresh or something
    def multipart_show(self, data: MultipartData) -> MultipartData:
        """Show details of the incomplete upload."""
        raise NotImplementedError

    def multipart_update(
        self,
        data: MultipartData,
        extras: dict[str, Any],
    ) -> MultipartData:
        """Add data to the incomplete upload."""
        raise NotImplementedError

    def multipart_complete(
        self,
        data: MultipartData,
        extras: dict[str, Any],
    ) -> FileData:
        """Verify file integrity and finalize incomplete upload."""

        raise NotImplementedError


class Manager(StorageService):
    def remove(self, data: FileData) -> bool:
        """Remove file from the storage."""
        raise NotImplementedError

    def exists(self, data: FileData) -> bool:
        """Check if file exists in the storage."""
        raise NotImplementedError

    def compose(
        self,
        datas: Iterable[FileData],
        location: str,
        extras: dict[str, Any],
    ) -> FileData:
        """Combine multipe file inside the storage into a new one."""

        raise NotImplementedError

    def append(
        self,
        data: FileData,
        upload: utils.Upload,
        extras: dict[str, Any],
    ) -> FileData:
        """Append content to existing file."""
        raise NotImplementedError

    def copy(
        self,
        data: FileData,
        location: str,
        extras: dict[str, Any],
    ) -> FileData:
        """Copy file inside the storage."""

        raise NotImplementedError

    def move(
        self,
        data: FileData,
        location: str,
        extras: dict[str, Any],
    ) -> FileData:
        """Move file to a different location inside the storage."""
        raise NotImplementedError

    def scan(self) -> Iterable[str]:
        """List all locations(filenames) in storage."""
        raise NotImplementedError

    def analyze(self, filename: str) -> FileData:
        """Return all details about filename."""
        raise NotImplementedError


class Reader(StorageService):
    def stream(self, data: FileData) -> IO[bytes]:
        """Return byte-stream of the file content."""
        raise NotImplementedError

    def content(self, data: FileData) -> bytes:
        """Return file content as a single byte object."""
        return self.stream(data).read()

    def permanent_link(self, data: FileData, extras: dict[str, Any]) -> str:
        """Return permanent download link."""
        raise NotImplementedError

    def temporal_link(self, data: FileData, extras: dict[str, Any]) -> str:
        """Return temporal download link."""
        raise NotImplementedError

    def one_time_link(self, data: FileData, extras: dict[str, Any]) -> str:
        """Return one-time download link."""
        raise NotImplementedError


class Storage(OptionChecker, abc.ABC):
    def __init__(self, **settings: Any) -> None:
        self.settings = settings

        self.uploader = self.make_uploader()
        self.manager = self.make_manager()
        self.reader = self.make_reader()

        self.capabilities = self.compute_capabilities()

    @property
    def max_size(self) -> int:
        """Max allowed upload size.

        Max size set to 0 removes all limitations.

        """

        size = self.settings.get("max_size", 0)
        return size

    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key) -> None:
        declaration.declare(key.max_size, 0).append_validators(
            "files_parse_filesize",
        ).set_description(
            "The maximum size of a single upload."
            + "\nSupports size suffixes: 42B, 2M, 24KiB, 1GB."
            + " `0` means no restrictions.",
        )
        declaration.declare(key.name, key[-1]).set_description(
            "Descriptive name of the storage used for debugging.",
        )

    def compute_capabilities(self) -> utils.Capability:
        return utils.Capability.combine(
            self.uploader.capabilities,
            self.manager.capabilities,
            self.reader.capabilities,
        )

    def make_uploader(self):
        return Uploader(self)

    def make_manager(self):
        return Manager(self)

    def make_reader(self):
        return Reader(self)

    def supports(self, operation: utils.Capability) -> bool:
        return self.capabilities.can(operation)

    def unsupported_operations(self):
        return utils.Capability.combine(*utils.Capability).exclude(self.capabilities)

    def compute_location(
        self,
        location: str,
        extras: dict[str, Any],
        upload: utils.Upload | None = None,
    ) -> str:
        strategy = self.settings.get("location_strategy", "uuid")

        if strategy == "transparent":
            return location

        if strategy == "uuid":
            return str(uuid.uuid4())

        if strategy == "uuid_prefix":
            return str(uuid.uuid4()) + location

        if strategy == "uuid_with_extension":
            _path, ext = os.path.splitext(location)
            return str(uuid.uuid4()) + ext

        if strategy == "datetime_prefix":
            return datetime.now(pytz.utc).isoformat() + location

        if strategy == "datetime_with_extension":
            _path, ext = os.path.splitext(location)
            return datetime.now(pytz.utc).isoformat() + ext

        raise exceptions.NameStrategyError(strategy)

    def upload(
        self,
        location: str,
        upload: utils.Upload,
        extras: dict[str, Any],
    ) -> FileData:
        if not self.supports(utils.Capability.CREATE):
            raise exceptions.UnsupportedOperationError("upload", type(self))

        if self.max_size:
            utils.ensure_size(upload, self.max_size)

        return self.uploader.upload(location, upload, extras)

    def multipart_start(
        self,
        name: str,
        extras: dict[str, Any],
    ) -> MultipartData:
        return self.uploader.multipart_start(name, extras)

    def multipart_show(self, upload_data: MultipartData) -> MultipartData:
        return self.uploader.multipart_show(upload_data)

    def multipart_update(
        self,
        upload_data: MultipartData,
        extras: dict[str, Any],
    ) -> MultipartData:
        return self.uploader.multipart_update(upload_data, extras)

    def multipart_complete(
        self,
        upload_data: MultipartData,
        extras: dict[str, Any],
    ) -> FileData:
        return self.uploader.multipart_complete(upload_data, extras)

    def exists(self, data: FileData) -> bool:
        if not self.supports(utils.Capability.EXISTS):
            raise exceptions.UnsupportedOperationError("exists", type(self))

        return self.manager.exists(data)

    def remove(self, data: FileData) -> bool:
        if not self.supports(utils.Capability.REMOVE):
            raise exceptions.UnsupportedOperationError("remove", type(self))

        return self.manager.remove(data)

    def scan(self) -> Iterable[str]:
        if not self.supports(utils.Capability.SCAN):
            raise exceptions.UnsupportedOperationError("scan", type(self))

        return self.manager.scan()

    def analyze(self, filename: str) -> FileData:
        if not self.supports(utils.Capability.ANALYZE):
            raise exceptions.UnsupportedOperationError("analyze", type(self))

        return self.manager.analyze(filename)

    def stream(self, data: FileData) -> IO[bytes]:
        if not self.supports(utils.Capability.STREAM):
            raise exceptions.UnsupportedOperationError("stream", type(self))

        return self.reader.stream(data)

    def content(self, data: FileData) -> bytes:
        if not self.supports(utils.Capability.STREAM):
            raise exceptions.UnsupportedOperationError("content", type(self))

        return self.reader.content(data)

    def copy(
        self,
        data: FileData,
        storage: Storage,
        location: str,
        extras: dict[str, Any],
    ) -> FileData:
        if storage is self and self.supports(utils.Capability.COPY):
            return self.manager.copy(data, location, extras)

        if self.supports(utils.Capability.STREAM) and storage.supports(
            utils.Capability.CREATE,
        ):
            return storage.upload(
                location,
                utils.make_upload(self.stream(data)),
                extras,
            )

        raise exceptions.UnsupportedOperationError("copy", type(self))

    def compose(
        self,
        storage: Storage,
        location: str,
        extras: dict[str, Any],
        *datas: FileData,
    ) -> FileData:
        if storage is self and self.supports(utils.Capability.COMPOSE):
            return self.manager.compose(datas, location, extras)

        if self.supports(utils.Capability.STREAM) and storage.supports(
            utils.Capability.combine(utils.Capability.CREATE, utils.Capability.APPEND),
        ):
            dest_data = storage.upload(location, utils.make_upload(""), extras)
            for data in datas:
                dest_data = storage.append(
                    dest_data,
                    utils.make_upload(self.stream(data)),
                    extras,
                )
            return dest_data

        raise exceptions.UnsupportedOperationError("compose", type(self))

    def append(
        self,
        data: FileData,
        upload: utils.Upload,
        extras: dict[str, Any],
    ) -> FileData:
        if self.supports(utils.Capability.APPEND):
            return self.manager.append(data, upload, extras)

        raise exceptions.UnsupportedOperationError("append", type(self))

    def move(
        self,
        data: FileData,
        storage: Storage,
        location: str,
        extras: dict[str, Any],
    ) -> FileData:
        if storage is self and self.supports(utils.Capability.MOVE):
            return self.manager.move(data, location, extras)

        if self.supports(
            utils.Capability.combine(
                utils.Capability.STREAM,
                utils.Capability.REMOVE,
            ),
        ) and storage.supports(utils.Capability.CREATE):
            result = storage.upload(
                location,
                utils.make_upload(self.stream(data)),
                extras,
            )
            storage.remove(data)
            return result

        raise exceptions.UnsupportedOperationError("copy", type(self))

    def link(
        self,
        data: FileData,
        extras: dict[str, Any],
        link_type: Literal["permanent", "temporal", "one-time", None] = None,
    ) -> str:
        if self.supports(utils.Capability.PERMANENT_LINK) and (
            not link_type or link_type == "permanent"
        ):
            return self.reader.permanent_link(data, extras)

        if self.supports(utils.Capability.TEMPORAL_LINK) and (
            not link_type or link_type == "temporal"
        ):
            return self.reader.temporal_link(data, extras)

        if self.supports(utils.Capability.ONE_TIME_LINK) and (
            not link_type or link_type == "one-time"
        ):
            return self.reader.one_time_link(data, extras)

        raise exceptions.UnsupportedOperationError("link", type(self))
