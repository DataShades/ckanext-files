import abc
import copy
import hashlib
import os
import uuid
from datetime import datetime

import six

import ckan.plugins.toolkit as tk

from ckanext.files import exceptions, utils

if six.PY3:
    from typing_extensions import TYPE_CHECKING, NewType, TypedDict

    from typing import Any, IO  # isort: skip # noqa: F401

    if TYPE_CHECKING:
        from werkzeug.datastructures import FileStorage  # isort: skip # noqa: F401

    MinimalStorageData = TypedDict(
        "MinimalStorageData",
        {
            "content_type": str,
            "size": int,
            "hash": str,
        },
    )

    CapabilityCluster = NewType("CapabilityCluster", int)
    CapabilityUnit = NewType("CapabilityUnit", int)

CHUNK_SIZE = 16384


class HashingReader:
    def __init__(self, stream, chunk_size=CHUNK_SIZE, algorithm="md5"):
        # type: (IO[bytes], int, str) -> None
        self.stream = stream
        self.chunk_size = chunk_size
        self.algorithm = algorithm
        self.hashsum = hashlib.new(algorithm)
        self.position = 0

    def __iter__(self):
        while True:
            chunk = self.stream.read(self.chunk_size)
            if not chunk:
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


class Capability(object):
    CREATE = 1 << 0  # type: CapabilityUnit
    STREAM = 1 << 1  # type: CapabilityUnit
    DOWNLOAD = 1 << 2  # type: CapabilityUnit
    REMOVE = 1 << 3  # type: CapabilityUnit
    MULTIPART_UPLOAD = 1 << 4  # type: CapabilityUnit


class OptionChecker(object):
    @classmethod
    def ensure_option(cls, settings, option):
        # type: (dict[str, Any], str) -> Any
        if option not in settings:
            raise exceptions.MissingAdapterConfigurationError(cls, option)
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
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def upload(self, name, upload, extras):
        # type: (str, FileStorage, dict[str, Any]) -> MinimalStorageData
        raise NotImplementedError

    def compute_name(self, name, extras, upload=None):
        # type: (str, dict[str, Any], FileStorage|None) -> str
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
        # type: (str, dict[str, Any]) -> dict[str, Any]
        raise NotImplementedError

    def update_multipart_upload(self, upload_data, extras):
        # type: (dict[str, Any], dict[str, Any]) -> dict[str, Any]
        raise NotImplementedError

    def complete_multipart_upload(self, upload_data, extras):
        # type: (dict[str, Any], dict[str, Any]) -> MinimalStorageData
        raise NotImplementedError


class Manager(StorageService):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def remove(self, data):
        # type: (dict[str, Any]) -> bool
        raise NotImplementedError


class Reader(StorageService):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def stream(self, data):
        # type: (dict[str, Any]) -> IO[str] | IO[bytes]
        raise NotImplementedError


class Storage(OptionChecker):
    __metaclass__ = abc.ABCMeta

    def __init__(self, **settings):
        # type: (**Any) -> None
        self.settings = settings

        self.uploader = self.make_uploader()
        self.manager = self.make_manager()
        self.reader = self.make_reader()

        self.capabilities = self.compute_capabilities()

    @property
    def max_size(self):
        return tk.asint(self.settings.get("max_size", 0))

    def compute_capabilities(self):
        # type: () -> CapabilityCluster
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
        # type: (CapabilityCluster | CapabilityUnit) -> bool
        return (self.capabilities & operation) == operation

    def upload(self, name, upload, extras):
        # type: (str, FileStorage, dict[str, Any]) -> dict[str, Any]
        if not self.supports(Capability.CREATE):
            raise exceptions.UnsupportedOperationError("upload", type(self).__name__)

        if self.max_size:
            utils.ensure_size(upload, self.max_size)

        return self.uploader.upload(name, upload, extras)

    def initialize_multipart_upload(self, name, extras):
        # type: (str, dict[str, Any]) -> dict[str, Any]
        return self.uploader.initialize_multipart_upload(name, extras)

    def update_multipart_upload(self, upload_data, extras):
        # type: (dict[str, Any], dict[str, Any]) -> dict[str, Any]
        return self.uploader.update_multipart_upload(copy.deepcopy(upload_data), extras)

    def complete_multipart_upload(self, upload_data, extras):
        # type: (dict[str, Any], dict[str, Any]) -> dict[str, Any]
        return self.uploader.complete_multipart_upload(
            copy.deepcopy(upload_data),
            extras,
        )

    def remove(self, data):
        # type: (dict[str, Any]) -> bool
        if not self.supports(Capability.REMOVE):
            raise exceptions.UnsupportedOperationError("remove", type(self).__name__)

        return self.manager.remove(data)
