"""Types for the extension.
"""

import enum

from typing_extensions import TypedDict
from werkzeug.datastructures import FileStorage as Upload

__all__ = [
    "Upload",
    "MinimalStorageData",
    "Capability",
]


MinimalStorageData = TypedDict(
    "MinimalStorageData",
    {"filename": str, "content_type": str, "size": int, "hash": str},
)


class Capability(enum.Flag):
    """Enumeration of operations supported by the storage.

    Do not assume internal implementation of this type. Use Storage.supports,
    utils.combine_capabilities, and utils.exclude_capabilities to check and
    modify capabilities of the storage.

    Example:
    >>> read_and_write = utils.combine_capabilities(
    >>>     Capability.STREAM, Capability.CREATE,
    >>> )
    >>> if storage.supports(read_and_write)
    >>>     ...
    """

    # create a file as an atomic object
    CREATE = enum.auto()
    # return file content as stream of bytes
    STREAM = enum.auto()
    # make a copy of the file inside the storage
    COPY = enum.auto()
    # remove file from the storage
    REMOVE = enum.auto()
    # create file in 3 stages: initialize, upload(repeatable), complete
    MULTIPART_UPLOAD = enum.auto()
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
