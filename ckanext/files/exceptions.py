"""Exception definitions for the extension.

Avoid raising python-native exceptions and prefere defining `FilesError`
subclass.

"""

import six

from ckan.lib.formatters import localised_filesize

if six.PY3:
    from typing import Any  # isort: skip # noqa: F401


class FilesError(Exception):
    pass


class StorageError(FilesError):
    pass


class UploadError(StorageError):
    pass


class UnknownStorageError(StorageError):
    """Storage with the given name is not configured."""

    def __init__(self, storage):
        # type: (str) -> None
        self.storage = storage

    def __str__(self):
        return "Storage {} is not configured".format(self.storage)


class UnknownAdapterError(StorageError):
    """Specified storage adapter is not registered."""

    def __init__(self, adapter):
        # type: (str) -> None
        self.adapter = adapter

    def __str__(self):
        return "Storage adapter {} is not registered".format(self.adapter)


class UnsupportedOperationError(StorageError):
    """Requested operation is not supported by storage."""

    def __init__(self, operation, adapter):
        # type: (Any, Any) -> None
        self.operation = operation
        self.adapter = adapter

    def __str__(self):
        return "Operation {} is not supported by storage adapter {}".format(
            self.operation,
            self.adapter,
        )


class InvalidStorageConfigurationError(StorageError):
    """Storage cannot be initialized with given configuration."""

    def __init__(self, adapter, problem):
        # type: (type, str) -> None
        self.adapter = adapter
        self.problem = problem

    def __str__(self):
        return "Cannot initialize storage adapter {} due to following error: {}".format(
            self.adapter.__name__,
            self.problem,
        )


class MissingStorageConfigurationError(InvalidStorageConfigurationError):
    """Storage cannot be initialized due to missing option."""

    def __init__(self, adapter, option):
        # type: (type, str) -> None
        return super(MissingStorageConfigurationError, self).__init__(
            adapter,
            "{} option is required".format(option),
        )


class MissingFileError(StorageError):
    """File does not exist."""

    def __init__(self, storage, filename):
        # type: (str, str) -> None
        self.storage = storage
        self.filename = filename

    def __str__(self):
        return "File {} does not exist inside {} storage".format(
            self.filename,
            self.storage,
        )


class LargeUploadError(UploadError):
    """Storage cannot be initialized due to missing option."""

    def __init__(self, actual_size, max_size):
        # type: (int, int) -> None
        self.actual_size = actual_size
        self.max_size = max_size

    def __str__(self):
        return "Upload size {} surpasses max allowed size {}".format(
            localised_filesize(self.actual_size),
            localised_filesize(self.max_size),
        )


class UploadOutOfBoundError(LargeUploadError):
    """Multipart upload exceeds expected size."""

    def __str__(self):
        return "Upload size {} exceeds expected size {}".format(
            localised_filesize(self.actual_size),
            localised_filesize(self.max_size),
        )


class NameStrategyError(UploadError):
    """Undefined name strategy."""

    def __init__(self, strategy):
        # type: (str) -> None
        self.strategy = strategy

    def __str__(self):
        return "Unknown name strategy {}".format(self.strategy)


class UploadExtrasError(UploadError):
    """Wrong extras passed during upload."""

    def __init__(self, extras):
        # type: (Any) -> None
        self.extras = extras

    def __str__(self):
        return "Wrong extras: {}".format(self.extras)


class MissingExtrasError(UploadExtrasError):
    """Wrong extras passed during upload."""

    def __init__(self, key):
        # type: (Any) -> None
        self.key = key

    def __str__(self):
        return "Key {} is missing from upload extras".format(self.key)
