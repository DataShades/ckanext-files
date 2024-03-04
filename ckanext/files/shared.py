from ckanext.files.exceptions import UnknownStorageError
from ckanext.files.storage import Capability, Manager, Reader, Storage, Uploader
from ckanext.files.utils import combine_capabilities, storages

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
