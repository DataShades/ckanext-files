"""Interfaces of the extension.
"""

from __future__ import annotations

from typing import Any, Callable

from ckan.plugins import Interface
from ckan.types import Context

from ckanext.files import types

File = Multipart = Any


class IFiles(Interface):
    """Extension point for ckanext-files."""

    def files_get_storage_adapters(self) -> dict[str, Any]:
        """Return mapping of storage type to adapter class.

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
        operation: types.AuthOperation,
        next_owner: Any | None,
    ) -> bool | None:
        """Decide if user is allowed to perform specified operation on the file.

        Return True/False if user allowed/not allowed. Return `None` to rely on
        other plugins. If every implementation returns `None`, default logic
        allows only user who owns the file to perform any operation on it. It
        means, that nobody is allowed to do anything with file owner by
        resource, dataset, group, etc.

        Example:
        >>> def files_is_allowed(
        >>>         self, context, file, operation, next_owner
        >>> ) -> bool | None:
        >>>     if file.owner_info and file.owner_info.owner_type == "resource":
        >>>         return is_authorized_boolean(
        >>>             f"resource_{operation}",
        >>>             context,
        >>>             {"id": file.owner_info.id}
        >>>         )
        >>>
        >>>     return None

        """
        return None
