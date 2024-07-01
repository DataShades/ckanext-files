"""Exception definitions for the extension.

Hierarchy:

* Exception
    * FilesError
        * QueueError
            * OutOfQueueError
        * StorageError
            * UnknownAdapterError
            * UnknownStorageError
            * UnsupportedOperationError
            * PermissionError
            * MissingFileError
            * ExistingFileError
            * ExtrasError
                * MissingExtrasError
            * InvalidStorageConfigurationError
                * MissingStorageConfigurationError
            * UploadError
                * WrongUploadTypeError
                * NameStrategyError
                * ContentError
                * LargeUploadError
                    * UploadOutOfBoundError
                * UploadMismatchError
                    * UploadTypeMismatchError
                    * UploadHashMismatchError
                    * UploadSizeMismatchError

"""

from __future__ import annotations

from typing import Any

Storage = Any


class FilesError(Exception):
    """Base error for catch-all scenario."""


class QueueError(FilesError):
    """Error related to task queue."""


class OutOfQueueError(QueueError):
    """Attempt to add task without initializing task queue context."""

    def __str__(self):
        return "Task queue accessed outside of queue context"


class StorageError(FilesError):
    """Error related to storage."""


class UnknownStorageError(StorageError):
    """Storage with the given name is not configured."""

    def __init__(self, storage: str):
        self.storage = storage

    def __str__(self):
        return f"Storage {self.storage} is not configured"


class UnknownAdapterError(StorageError):
    """Specified storage adapter is not registered."""

    def __init__(self, adapter: str):
        self.adapter = adapter

    def __str__(self):
        return f"Storage adapter {self.adapter} is not registered"


class UnsupportedOperationError(StorageError):
    """Requested operation is not supported by storage."""

    def __init__(self, operation: str, storage: Storage):
        self.operation = operation
        self.storage = storage

    def __str__(self):
        return f"Operation {self.operation} is not supported by {self.storage} storage"


class InvalidStorageConfigurationError(StorageError):
    """Storage cannot be initialized with given configuration."""

    def __init__(self, adapter: type, problem: str):
        self.adapter = adapter
        self.problem = problem

    def __str__(self):
        return (
            f"Cannot initialize storage adapter {self.adapter.__name__}"
            + f" due to following error: {self.problem}"
        )


class PermissionError(StorageError):
    """Storage client does not have required permissions."""

    def __init__(self, storage: Storage, operation: str, problem: str):
        self.storage = storage
        self.operation = operation
        self.problem = problem

    def __str__(self):
        msg = "Storage {} is not allowed to perform {} operation: {}"
        return msg.format(
            self.storage,
            self.operation,
            self.problem,
        )


class MissingStorageConfigurationError(InvalidStorageConfigurationError):
    """Storage cannot be initialized due to missing option."""

    def __init__(self, adapter: type, option: str):
        super().__init__(
            adapter,
            f"{option} option is required",
        )


class MissingFileError(StorageError):
    """File does not exist."""

    def __init__(self, storage: Storage, filename: str):
        self.storage = storage
        self.filename = filename

    def __str__(self):
        return f"File {self.filename} does not exist inside storage {self.storage}"


class ExistingFileError(StorageError):
    """File already exists."""

    def __init__(self, storage: Storage, filename: str):
        self.storage = storage
        self.filename = filename

    def __str__(self):
        return f"File {self.filename} already exists inside storage {self.storage}"


class UploadError(StorageError):
    """Error related to file upload process."""


class LargeUploadError(UploadError):
    """Storage cannot be initialized due to missing option."""

    def __init__(self, actual_size: int, max_size: int):
        self.actual_size = actual_size
        self.max_size = max_size

    def __str__(self):
        return (
            f"Upload size {self.actual_size} surpasses"
            + f" max allowed size {self.max_size}"
        )


class UploadOutOfBoundError(LargeUploadError):
    """Multipart upload exceeds expected size."""

    def __str__(self):
        return (
            f"Upload size {self.actual_size} exceeds"
            + f" expected size {self.max_size}"
        )


class UploadMismatchError(UploadError):
    """Expected value of file attribute doesn't match the actual value."""

    value_formatter = str

    def __init__(self, attribute: str, actual: Any, expected: Any):
        self.attribute = attribute
        self.actual = actual
        self.expected = expected

    def __str__(self):
        actual = self.value_formatter(self.actual)
        expected = self.value_formatter(self.expected)
        return (
            f"Actual value of {self.attribute}({actual}) does not"
            + f" match expected value({expected})"
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
        return f"Type {self.content_type} is not supported by storage"


class NameStrategyError(UploadError):
    """Undefined name strategy."""

    def __init__(self, strategy: str):
        self.strategy = strategy

    def __str__(self):
        return f"Unknown name strategy {self.strategy}"


class ExtrasError(StorageError):
    """Wrong extras passed during upload."""

    def __init__(self, extras: Any):
        self.extras = extras

    def __str__(self):
        return f"Wrong extras: {self.extras}"


class MissingExtrasError(ExtrasError):
    """Wrong extras passed to storage method."""

    def __init__(self, key: Any):
        self.key = key

    def __str__(self):
        return f"Key {self.key} is missing from extras"


class ContentError(UploadError):
    """Storage cannot accept uploaded content."""

    def __init__(self, storage: Storage, msg: str):
        self.storage = storage
        self.msg = msg

    def __str__(self):
        return f"{self.storage} rejected upload: {self.msg}"
