"""Interfaces of the extension.
"""

from __future__ import annotations

from typing import Any, Callable

from ckan.plugins import Interface
from ckan.types import Context

from ckanext.files import utils

File = Multipart = Any


class IFiles(Interface):
    """Extension point for ckanext-files."""

    def files_get_storage_adapters(self) -> dict[str, Any]:
        """Return mapping of storage type to storage factory.

        Example:
        >>> def files_get_storage_adapters(self):
        >>>     return {
        >>>         "my_ext:dropbox": DropboxStorage,
        >>>     }

        """

        return {}

    def files_register_owner_getters(self) -> dict[str, Callable[[str], Any]]:
        """Return mapping with lookup functions for owner types.

        Name of the getter is the name used as `Owner.owner_type`. The getter
        itself is a function that accepts owner ID and returns optional owner
        entity.

        Example:
        >>> def files_register_owner_getters(self):
        >>>     return {"resource": model.Resource.get}
        """
        return {}

    def files_is_allowed(
        self,
        context: Context,
        file: File | Multipart | None,
        owner: Any | None,
        operation: utils.AuthOperation,
    ) -> bool | None:
        """Decide if user is allowed to perform operation on file that belongs
        to owner.

        Return True/False if user allowed/not allowed. Return `None` to rely on
        other plugins. If every implementation returns `None`, default logic
        allows only user who owns the file to perform any operation on it. It
        means, that nobody is allowed to do anything with file owner by
        resource, dataset, group, etc.

        For `show`, `update` and `delete` operation, `owner` represents the
        current owner of the file. For `file_transfer` operation, `owner`
        represents the entity that will become a new owner of the file. In this
        case, the current owner can be checked via `file.owner` property.

        Example:
        >>> def files_is_allowed(self, context, file, owner, operation) -> bool | None:
        >>>     if isinstance(owner, model.Resource):
        >>>         return is_authorized_boolean(
        >>>             f"resource_{operation}",
        >>>             context,
        >>>             {"id": file.owner_info.id}
        >>>         )
        >>>
        >>>     return None

        """
        return None
