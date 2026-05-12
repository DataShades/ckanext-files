from file_keeper import Capability, FileData, HashingReader, Location, Upload, exc, make_storage, make_upload

try:
    from ckan.lib.files import Manager, Reader, Settings, Storage, Uploader, get_storage
    from ckan.plugins.interfaces import IFiles

except ImportError:
    from .base import Manager, Reader, Settings, Storage, Uploader, get_storage
    from .interfaces import IFiles

from . import config, types
from .model import File, Owner, TransferHistory
from .task import Task, TaskQueue, add_task, with_task_queue

__all__ = [
    "get_storage",
    "make_storage",
    "make_upload",
    "Upload",
    "HashingReader",
    "Capability",
    "File",
    "Location",
    "Owner",
    "TransferHistory",
    "FileData",
    "IFiles",
    "Storage",
    "Settings",
    "Uploader",
    "Reader",
    "Manager",
    "add_task",
    "with_task_queue",
    "Task",
    "TaskQueue",
    "types",
    "config",
    "exc",
]
