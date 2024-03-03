import uuid
import logging
import six
import os
import abc
from werkzeug.datastructures import FileStorage
from ckanext.files import exceptions, utils
import ckan.plugins.toolkit as tk

if six.PY3:
    from typing import Any, Iterable, IO
    from typing_extensions import NewType

    CapabilityCluster = NewType("CapabilityCluster", int)
    CapabilityUnit = NewType("CapabilityUnit", int)


class Capability(object):
    CREATE = 1 << 0  # type: CapabilityUnit
    STREAM = 1 << 1  # type: CapabilityUnit
    DOWNLOAD = 1 << 2  # type: CapabilityUnit
    REMOVE = 1 << 3  # type: CapabilityUnit


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
        # type: (str, FileStorage, dict[str, Any]) -> dict[str, Any]
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

        max_size = tk.asint(self.settings.get("max_size", 0))

        if max_size:
            utils.ensure_size(upload, max_size)

        return self.uploader.upload(name, upload, extras)

    def remove(self, data):
        # type: (dict[str, Any]) -> bool
        if not self.supports(Capability.REMOVE):
            raise exceptions.UnsupportedOperationError("remove", type(self).__name__)

        return self.manager.remove(data)
