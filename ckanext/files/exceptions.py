import six

from ckan.lib.formatters import localised_filesize

if six.PY3:
    pass


class FilesError(Exception):
    pass


class AdapterError(FilesError):
    pass


class StorageError(FilesError):
    pass


class UploadError(FilesError):
    pass


class UnknownStorageError(StorageError):
    """Storage with the given name is not configured."""

    def __init__(self, storage):
        # type: (str) -> None
        self.storage = storage

    def __str__(self):
        return "Storage {} is not configured".format(self.storage)


class UnknownAdapterError(AdapterError):
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
            self.operation, self.adapter
        )


class InvalidAdapterConfigurationError(AdapterError):
    """Adapter cannot be initialized with given configuration."""

    def __init__(self, adapter, problem):
        # type: (type, str) -> None
        self.adapter = adapter
        self.problem = problem

    def __str__(self):
        return "Cannot initialize storage adapter {} due to following error: {}".format(
            self.adapter.__name__, self.problem
        )


class MissingAdapterConfigurationError(InvalidAdapterConfigurationError):
    """Adapter cannot be initialized due to missing option."""

    def __init__(self, adapter, option):
        # type: (type, str) -> None
        return super(InvalidAdapterConfigurationError, self).__init__(
            adapter, "{} option is required".format(option)
        )


class LargeUploadError(UploadError):
    """Adapter cannot be initialized due to missing option."""

    def __init__(self, actual_size, max_size):
        # type: (int, int) -> None
        self.actual_size = actual_size
        self.max_size = max_size

    def __str__(self):
        return "Upload size {} surpasses max allowed size {}".format(
            localised_filesize(self.actual_size), localised_filesize(self.max_size)
        )
