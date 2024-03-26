"""Base abstract functionality of the extentsion.

All classes required for specific storage implementations are defined
here. Some utilities, like `storage_from_settings` are also added to this
module instead of `utils` to avoid import cycles.

This module relies only on types, exceptions and utils to prevent import
cycles.

"""

import abc
import copy
import hashlib
import os
import uuid
from datetime import datetime

from werkzeug.datastructures import FileStorage

from ckanext.files import exceptions, types, utils

CHUNK_SIZE = 16 * 1024
adapters = utils.Registry({})
storages = utils.Registry({})


def storage_from_settings(name, settings):
    # type: (str, dict[str, types.Any]) -> Storage

    adapter_type = settings.pop("type", None)
    adapter = adapters.get(adapter_type)  # type: type[Storage] | None
    if not adapter:
        raise exceptions.UnknownAdapterError(adapter_type)

    settings.setdefault("name", name)
    return adapter(**settings)


def get_storage(name):
    # type: (str) -> Storage
    storage = storages.get(name)

    if not storage:
        raise exceptions.UnknownStorageError(name)

    return storage


class HashingReader:
    def __init__(self, stream, chunk_size=CHUNK_SIZE, algorithm="md5"):
        # type: (types.IO[bytes], int, str) -> None
        self.stream = stream
        self.chunk_size = chunk_size
        self.algorithm = algorithm
        self.hashsum = hashlib.new(algorithm)
        self.position = 0

    def __iter__(self):
        while True:
            chunk = self.stream.read(self.chunk_size)
            if not chunk:
                yield chunk
                break
            self.position += len(chunk)
            self.hashsum.update(chunk)
            yield chunk

    def reset(self):
        self.position = 0
        self.hashsum = hashlib.new(self.algorithm)
        self.stream.seek(0)

    def get_hash(self):
        return self.hashsum.hexdigest()

    def exhaust(self):
        for _ in self:
            pass


class Capability(object):
    CREATE = types.CapabilityUnit(1 << 0)
    STREAM = types.CapabilityUnit(1 << 1)
    COPY = types.CapabilityUnit(1 << 2)
    REMOVE = types.CapabilityUnit(1 << 3)
    MULTIPART_UPLOAD = types.CapabilityUnit(1 << 4)
    MOVE = types.CapabilityUnit(1 << 5)
    EXISTS = types.CapabilityUnit(1 << 6)


class OptionChecker(object):
    @classmethod
    def ensure_option(cls, settings, option):
        # type: (dict[str, types.Any], str) -> types.Any
        if option not in settings:
            raise exceptions.MissingStorageConfigurationError(cls, option)
        return settings[option]


class StorageService(OptionChecker):
    required_options = []  # type: list[str]
    capabilities = utils.combine_capabilities()

    def __init__(self, storage):
        # type: (Storage) -> None
        self.storage = storage
        self.ensure_settings()

    def ensure_settings(self):
        for option in self.required_options:
            self.ensure_option(self.storage.settings, option)


class Uploader(StorageService):
    def upload(self, name, upload, extras):
        # type: (str, types.Upload, dict[str, types.Any]) -> types.MinimalStorageData
        raise NotImplementedError

    def copy(self, data, name, extras):
        # type: (types.MinimalStorageData, str, dict[str, types.Any]) -> types.MinimalStorageData
        raise NotImplementedError

    def move(self, data, name, extras):
        # type: (types.MinimalStorageData, str, dict[str, types.Any]) -> types.MinimalStorageData
        raise NotImplementedError

    def compute_name(self, name, extras, upload=None):
        # type: (str, dict[str, types.Any], types.Upload|None) -> str
        strategy = self.storage.settings.get("name_strategy", "uuid")
        if strategy == "uuid":
            return str(uuid.uuid4())

        if strategy == "uuid_prefix":
            return str(uuid.uuid4()) + name

        if strategy == "datetime_prefix":
            return datetime.utcnow().isoformat() + name

        if strategy == "uuid_with_extension":
            _path, ext = os.path.splitext(name)
            return str(uuid.uuid4()) + ext

        if strategy == "datetime_with_extension":
            _path, ext = os.path.splitext(name)
            return datetime.utcnow().isoformat() + ext

        raise exceptions.NameStrategyError(strategy)

    def initialize_multipart_upload(self, name, extras):
        # type: (str, dict[str, types.Any]) -> dict[str, types.Any]
        raise NotImplementedError

    def show_multipart_upload(self, upload_data):
        # type: (dict[str, types.Any]) -> dict[str, types.Any]
        raise NotImplementedError

    def update_multipart_upload(self, upload_data, extras):
        # type: (dict[str, types.Any], dict[str, types.Any]) -> dict[str, types.Any]
        raise NotImplementedError

    def complete_multipart_upload(self, upload_data, extras):
        # type: (dict[str, types.Any], dict[str, types.Any]) -> types.MinimalStorageData
        raise NotImplementedError


class Manager(StorageService):
    def remove(self, data):
        # type: (dict[str, types.Any]) -> bool
        raise NotImplementedError

    def exists(self, data):
        # type: (dict[str, types.Any]) -> bool
        raise NotImplementedError


class Reader(StorageService):
    def stream(self, data):
        # type: (dict[str, types.Any]) -> types.IO[bytes]
        raise NotImplementedError

    def content(self, data):
        # type: (dict[str, types.Any]) -> bytes
        return self.stream(data).read()


class Storage(OptionChecker):
    __metaclass__ = abc.ABCMeta

    def __init__(self, **settings):
        # type: (**types.Any) -> None
        self.settings = settings

        self.uploader = self.make_uploader()
        self.manager = self.make_manager()
        self.reader = self.make_reader()

        self.capabilities = self.compute_capabilities()

    @property
    def max_size(self):
        size = self.settings.get("max_size", 0)

        # pre v2.10 CKAN instances do not support config declarations
        if isinstance(size, str):
            size = utils.parse_filesize(size)

        return size

    @classmethod
    def declare_config_options(cls, declaration, key):
        # type: (types.Declaration, types.Key) -> None
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

    def compute_capabilities(self):
        # type: () -> types.CapabilityCluster
        return utils.combine_capabilities(
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

    def supports(self, operation):
        # type: (types.CapabilityCluster | types.CapabilityUnit) -> bool
        return (self.capabilities & operation) == operation

    def upload(self, name, upload, extras):
        # type: (str, types.Upload, dict[str, types.Any]) -> types.MinimalStorageData
        if not self.supports(Capability.CREATE):
            raise exceptions.UnsupportedOperationError("upload", type(self).__name__)

        if self.max_size:
            utils.ensure_size(upload, self.max_size)

        return self.uploader.upload(name, upload, extras)

    def initialize_multipart_upload(self, name, extras):
        # type: (str, dict[str, types.Any]) -> dict[str, types.Any]
        return self.uploader.initialize_multipart_upload(name, extras)

    def show_multipart_upload(self, upload_data):
        # type: (dict[str, types.Any]) -> dict[str, types.Any]
        return self.uploader.show_multipart_upload(copy.deepcopy(upload_data))

    def update_multipart_upload(self, upload_data, extras):
        # type: (dict[str, types.Any], dict[str, types.Any]) -> dict[str, types.Any]
        return self.uploader.update_multipart_upload(copy.deepcopy(upload_data), extras)

    def complete_multipart_upload(self, upload_data, extras):
        # type: (dict[str, types.Any], dict[str, types.Any]) -> types.MinimalStorageData
        return self.uploader.complete_multipart_upload(
            copy.deepcopy(upload_data),
            extras,
        )

    def exists(self, data):
        # type: (dict[str, types.Any]) -> bool
        if not self.supports(Capability.EXISTS):
            raise exceptions.UnsupportedOperationError("exists", type(self).__name__)

        return self.manager.exists(data)

    def remove(self, data):
        # type: (dict[str, types.Any]) -> bool
        if not self.supports(Capability.REMOVE):
            raise exceptions.UnsupportedOperationError("remove", type(self).__name__)

        return self.manager.remove(data)

    def stream(self, data):
        # type: (dict[str, types.Any]) -> types.IO[bytes]
        if not self.supports(Capability.STREAM):
            raise exceptions.UnsupportedOperationError("stream", type(self).__name__)

        return self.reader.stream(data)

    def content(self, data):
        # type: (dict[str, types.Any]) -> bytes | str
        if not self.supports(Capability.STREAM):
            raise exceptions.UnsupportedOperationError("content", type(self).__name__)

        return self.reader.content(data)

    def copy(self, data, storage, name, extras):
        # type: (dict[str, types.Any], Storage, str, dict[str, types.Any]) -> types.MinimalStorageData
        if storage is self and self.supports(Capability.COPY):
            return self.uploader.copy(data, name, extras)

        if self.supports(Capability.STREAM) and storage.supports(Capability.CREATE):
            return storage.upload(name, FileStorage(self.stream(data)), extras)

        raise exceptions.UnsupportedOperationError("copy", type(self).__name__)

    def move(self, data, storage, name, extras):
        # type: (dict[str, types.Any], Storage, str, dict[str, types.Any]) -> types.MinimalStorageData

        if storage is self and self.supports(Capability.MOVE):
            return self.uploader.move(data, name, extras)

        if self.supports(
            utils.combine_capabilities(Capability.STREAM, Capability.REMOVE),
        ) and storage.supports(Capability.CREATE):
            result = storage.upload(name, FileStorage(self.stream(data)), extras)
            storage.remove(data)
            return result

        raise exceptions.UnsupportedOperationError("copy", type(self).__name__)
