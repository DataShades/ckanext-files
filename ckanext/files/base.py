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

from . import config, exceptions, model, utils
from .types import TFileModel

adapters = utils.Registry["type[Storage]"]({})
storages = utils.Registry["Storage"]({})


def ensure_size(upload: utils.Upload, max_size: int) -> int:
    """Return filesize or rise an exception if it exceedes max_size."""

    if upload.size > max_size:
        raise exceptions.LargeUploadError(upload.size, max_size)

    return upload.size


def ensure_type(upload: utils.Upload, types: list[str]) -> str:
    """Return content type of upload or rise an exception if type is not supported"""

    maintype, subtype = upload.content_type.split("/")
    for option in types:
        if option in [upload.content_type, maintype, subtype]:
            return upload.content_type

    raise exceptions.WrongUploadTypeError(upload.content_type)


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
        data: MultipartData,
        extras: dict[str, Any],
    ) -> MultipartData:
        """Prepare everything for multipart(resumable) upload."""

        raise NotImplementedError

    # TODO: rename to refresh or something
    def multipart_refresh(
        self,
        data: MultipartData,
        extras: dict[str, Any],
    ) -> MultipartData:
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
    def remove(self, data: FileData | MultipartData, extras: dict[str, Any]) -> bool:
        """Remove file from the storage."""
        raise NotImplementedError

    def exists(self, data: FileData, extras: dict[str, Any]) -> bool:
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

    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        """List all locations(filenames) in storage."""
        raise NotImplementedError

    def analyze(self, location: str, extras: dict[str, Any]) -> FileData:
        """Return all details about filename."""
        raise NotImplementedError


class Reader(StorageService):
    def stream(self, data: FileData, extras: dict[str, Any]) -> IO[bytes]:
        """Return byte-stream of the file content."""
        raise NotImplementedError

    def content(self, data: FileData, extras: dict[str, Any]) -> bytes:
        """Return file content as a single byte object."""
        return self.stream(data, extras).read()

    def permanent_link(self, data: FileData, extras: dict[str, Any]) -> str:
        """Return permanent download link."""
        raise NotImplementedError

    def temporal_link(self, data: FileData, extras: dict[str, Any]) -> str:
        """Return temporal download link."""
        raise NotImplementedError

    def one_time_link(self, data: FileData, extras: dict[str, Any]) -> str:
        """Return one-time download link."""
        raise NotImplementedError

    def public_link(self, data: FileData, extras: dict[str, Any]) -> str:
        """Return public link."""
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

    @property
    def supported_types(self) -> list[str]:
        """List of supported MIMEtypes or their parts."""

        return self.settings.get("supported_types", [])

    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key) -> None:
        declaration.declare(key.max_size, 0).append_validators(
            "files_parse_filesize",
        ).set_description(
            "The maximum size of a single upload."
            + "\nSupports size suffixes: 42B, 2M, 24KiB, 1GB."
            + " `0` means no restrictions.",
        )
        declaration.declare_list(key.supported_types, None).set_description(
            "Space-separated list of MIME types or just type or subtype part."
            + "\nExample: text/csv pdf application video jpeg",
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
        upload: utils.Upload | None = None,
        /,
        **kwargs: Any,
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

    def upload(self, location: str, upload: utils.Upload, /, **kwargs: Any) -> FileData:
        if not self.supports(utils.Capability.CREATE):
            raise exceptions.UnsupportedOperationError("upload", type(self))

        if self.max_size:
            ensure_size(upload, self.max_size)

        if self.supported_types:
            ensure_type(upload, self.supported_types)

        return self.uploader.upload(location, upload, kwargs)

    def multipart_start(
        self,
        name: str,
        data: MultipartData,
        /,
        **kwargs: Any,
    ) -> MultipartData:
        return self.uploader.multipart_start(name, data, kwargs)

    def multipart_refresh(self, data: MultipartData, /, **kwargs: Any) -> MultipartData:
        return self.uploader.multipart_refresh(data, kwargs)

    def multipart_update(self, data: MultipartData, /, **kwargs: Any) -> MultipartData:
        return self.uploader.multipart_update(data, kwargs)

    def multipart_complete(self, data: MultipartData, /, **kwargs: Any) -> FileData:
        return self.uploader.multipart_complete(data, kwargs)

    def exists(self, data: FileData, /, **kwargs: Any) -> bool:
        if not self.supports(utils.Capability.EXISTS):
            raise exceptions.UnsupportedOperationError("exists", type(self))

        return self.manager.exists(data, kwargs)

    def remove(self, data: FileData | MultipartData, /, **kwargs: Any) -> bool:
        if not self.supports(utils.Capability.REMOVE):
            raise exceptions.UnsupportedOperationError("remove", type(self))

        return self.manager.remove(data, kwargs)

    def scan(self, **kwargs: Any) -> Iterable[str]:
        if not self.supports(utils.Capability.SCAN):
            raise exceptions.UnsupportedOperationError("scan", type(self))

        return self.manager.scan(kwargs)

    def analyze(self, location: str, /, **kwargs: Any) -> FileData:
        if not self.supports(utils.Capability.ANALYZE):
            raise exceptions.UnsupportedOperationError("analyze", type(self))

        return self.manager.analyze(location, kwargs)

    def stream(self, data: FileData, /, **kwargs: Any) -> IO[bytes]:
        if not self.supports(utils.Capability.STREAM):
            raise exceptions.UnsupportedOperationError("stream", type(self))

        return self.reader.stream(data, kwargs)

    def content(self, data: FileData, /, **kwargs: Any) -> bytes:
        if not self.supports(utils.Capability.STREAM):
            raise exceptions.UnsupportedOperationError("content", type(self))

        return self.reader.content(data, kwargs)

    def copy(
        self,
        data: FileData,
        storage: Storage,
        location: str,
        /,
        **kwargs: Any,
    ) -> FileData:
        if storage is self and self.supports(utils.Capability.COPY):
            return self.manager.copy(data, location, kwargs)

        if self.supports(utils.Capability.STREAM) and storage.supports(
            utils.Capability.CREATE,
        ):
            return storage.upload(
                location,
                utils.make_upload(self.stream(data)),
                **kwargs,
            )

        raise exceptions.UnsupportedOperationError("copy", type(self))

    def compose(
        self,
        storage: Storage,
        location: str,
        /,
        *datas: FileData,
        **kwargs: Any,
    ) -> FileData:
        if storage is self and self.supports(utils.Capability.COMPOSE):
            return self.manager.compose(datas, location, kwargs)

        if self.supports(utils.Capability.STREAM) and storage.supports(
            utils.Capability.combine(utils.Capability.CREATE, utils.Capability.APPEND),
        ):
            dest_data = storage.upload(location, utils.make_upload(""), **kwargs)
            for data in datas:
                dest_data = storage.append(
                    dest_data,
                    utils.make_upload(self.stream(data)),
                    **kwargs,
                )
            return dest_data

        raise exceptions.UnsupportedOperationError("compose", type(self))

    def append(
        self,
        data: FileData,
        upload: utils.Upload,
        /,
        **kwargs: Any,
    ) -> FileData:
        if self.supports(utils.Capability.APPEND):
            return self.manager.append(data, upload, kwargs)

        raise exceptions.UnsupportedOperationError("append", type(self))

    def move(
        self,
        data: FileData,
        storage: Storage,
        location: str,
        /,
        **kwargs: Any,
    ) -> FileData:
        if storage is self and self.supports(utils.Capability.MOVE):
            return self.manager.move(data, location, kwargs)

        if self.supports(
            utils.Capability.combine(
                utils.Capability.STREAM,
                utils.Capability.REMOVE,
            ),
        ) and storage.supports(utils.Capability.CREATE):
            result = storage.upload(
                location,
                utils.make_upload(self.stream(data)),
                **kwargs,
            )
            storage.remove(data)
            return result

        raise exceptions.UnsupportedOperationError("copy", type(self))

    def public_link(
        self,
        data: FileData,
        /,
        **kwargs: Any,
    ) -> str:
        if self.supports(utils.Capability.PUBLIC_LINK):
            return self.reader.public_link(data, kwargs)

        raise exceptions.UnsupportedOperationError("public link", type(self))

    def private_link(
        self,
        data: FileData,
        link_type: Literal["permanent", "temporal", "one-time"] | None = None,
        /,
        **kwargs: Any,
    ) -> str:
        if self.supports(utils.Capability.ONE_TIME_LINK) and (
            not link_type or link_type == "one-time"
        ):
            return self.reader.one_time_link(data, kwargs)

        if self.supports(utils.Capability.TEMPORAL_LINK) and (
            not link_type or link_type == "temporal"
        ):
            return self.reader.temporal_link(data, kwargs)

        if self.supports(utils.Capability.PERMANENT_LINK) and (
            not link_type or link_type == "permanent"
        ):
            return self.reader.permanent_link(data, kwargs)

        raise exceptions.UnsupportedOperationError("private link", type(self))
