from ckanext.files.base import Capability, Manager, Reader, Storage, Uploader, storages
from ckanext.files.exceptions import UnknownStorageError
from ckanext.files.utils import combine_capabilities

__all__ = [
    "combine_capabilities",
    "get_storage",
    "Storage",
    "Uploader",
    "Reader",
    "Manager",
    "Capability",
]


def get_storage(name):
    # type: (str) -> Storage
    storage = storages.get(name)

    if not storage:
        raise UnknownStorageError(name)

    return storage
