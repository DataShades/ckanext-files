"""Exception definitions for the extension.

Avoid raising python-native exceptions and prefere defining `FilesError`
subclass.

"""

from __future__ import annotations

from typing import Any


class FilesError(Exception):
    pass


class StorageError(FilesError):
    pass


class UploadError(StorageError):
    pass


class UnknownStorageError(StorageError):
    """Storage with the given name is not configured."""

    def __init__(self, storage: str):
        self.storage = storage

    def __str__(self):
        return "Storage {} is not configured".format(self.storage)


class UnknownAdapterError(StorageError):
    """Specified storage adapter is not registered."""

    def __init__(self, adapter: str):
        self.adapter = adapter

    def __str__(self):
        return "Storage adapter {} is not registered".format(self.adapter)


class UnsupportedOperationError(StorageError):
    """Requested operation is not supported by storage."""

    def __init__(self, operation: str, adapter: type):
        self.operation = operation
        self.adapter = adapter

    def __str__(self):
        return "Operation {} is not supported by storage adapter {}".format(
            self.operation,
            self.adapter,
        )


class InvalidStorageConfigurationError(StorageError):
    """Storage cannot be initialized with given configuration."""

    def __init__(self, adapter: type, problem: str):
        self.adapter = adapter
        self.problem = problem

    def __str__(self):
        return "Cannot initialize storage adapter {} due to following error: {}".format(
            self.adapter.__name__,
            self.problem,
        )


class PermissionError(StorageError):
    """Storage client does not have required permissions."""

    def __init__(self, adapter: type, operation: str, problem: str):
        self.adapter = adapter
        self.operation = operation
        self.problem = problem

    def __str__(self):
        msg = "Storage {} is not allowed to perform {} operation: {}"
        return msg.format(
            self.adapter.__name__,
            self.operation,
            self.problem,
        )


class MissingStorageConfigurationError(InvalidStorageConfigurationError):
    """Storage cannot be initialized due to missing option."""

    def __init__(self, adapter: type, option: str):
        return super(MissingStorageConfigurationError, self).__init__(
            adapter,
            "{} option is required".format(option),
        )


class MissingFileError(StorageError):
    """File does not exist."""

    def __init__(self, storage: str, filename: str):
        self.storage = storage
        self.filename = filename

    def __str__(self):
        return "File {} does not exist inside storage {}".format(
            self.filename,
            self.storage,
        )


class ExistingFileError(StorageError):
    """File already exists."""

    def __init__(self, storage: str, filename: str):
        self.storage = storage
        self.filename = filename

    def __str__(self):
        return "File {} already exists inside storage {}".format(
            self.filename,
            self.storage,
        )


class LargeUploadError(UploadError):
    """Storage cannot be initialized due to missing option."""

    def __init__(self, actual_size: int, max_size: int):
        self.actual_size = actual_size
        self.max_size = max_size

    def __str__(self):
        return "Upload size {} surpasses max allowed size {}".format(
            self.actual_size,
            self.max_size,
        )


class UploadOutOfBoundError(LargeUploadError):
    """Multipart upload exceeds expected size."""

    def __str__(self):
        return "Upload size {} exceeds expected size {}".format(
            self.actual_size,
            self.max_size,
        )


class UploadMismatchError(UploadError):
    """Expected value of file attribute doesn't match the actual value."""

    value_formatter = str

    def __init__(self, attribute: str, actual: Any, expected: Any):
        self.attribute = attribute
        self.actual = actual
        self.expected = expected

    def __str__(self):
        return "Actual value of {}({}) does not match expected value({})".format(
            self.attribute,
            self.value_formatter(self.actual),
            self.value_formatter(self.expected),
        )


class UploadTypeMismatchError(UploadMismatchError):
    """Expected value of content type doesn't match the actual value."""

    def __init__(self, actual: Any, expected: Any):
        super().__init__("content type", actual, expected)


class UploadHashMismatchError(UploadMismatchError):
    """Expected value of hash match the actual value."""

    def __init__(self, actual: Any, expected: Any):
        super().__init__("content hash", actual, expected)


class UploadSizeMismatchError(UploadMismatchError):
    """Expected value of upload size doesn't match the actual value."""

    def __init__(self, actual: Any, expected: Any):
        super().__init__("upload size", actual, expected)


class WrongUploadTypeError(UploadError):
    """Storage does not support given MIMEType."""

    def __init__(self, content_type: str):
        self.content_type = content_type

    def __str__(self):
        return "Type {} is not supported by storage".format(self.content_type)


class NameStrategyError(UploadError):
    """Undefined name strategy."""

    def __init__(self, strategy: str):
        self.strategy = strategy

    def __str__(self):
        return "Unknown name strategy {}".format(self.strategy)


class UploadExtrasError(UploadError):
    """Wrong extras passed during upload."""

    def __init__(self, extras: Any):
        self.extras = extras

    def __str__(self):
        return "Wrong extras: {}".format(self.extras)


class MissingExtrasError(UploadExtrasError):
    """Wrong extras passed during upload."""

    def __init__(self, key: Any):
        self.key = key

    def __str__(self):
        return "Key {} is missing from upload extras".format(self.key)
