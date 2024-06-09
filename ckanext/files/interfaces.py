"""Interfaces of the extension.
"""

from __future__ import annotations

from typing import Any

from ckan.plugins import Interface
from ckan.types import Context

from ckanext.files import types

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

    def files_materialize_owner(
        self,
        owner_type: str,
        owner_id: str,
        not_exist: object,
    ) -> Any:
        """Return owner entity.

        If implementation doesn't know how to get owner, return `None`. If
        implementation knows how to get owner and owner **definitely** does not
        exist, return `not_exist` parameter.

        Example:
        >>> def files_materialize_owner(self, type, id, not_exist):
        >>>     if type not in known_types:
        >>>         return None
        >>>
        >>>     if owner := get_known_owner(id):
        >>>         return owner
        >>>
        >>>     return not_exist
        """
        return None

    def files_is_allowed(
        self,
        context: Context,
        file: File | Multipart,
        operation: types.AuthOperation,
    ) -> bool | None:
        """Decide if user is allowed to perform operation on file.

        Return True/False if user allowed/not allowed. Return `None` to rely on
        other plugins. If every implementation returns `None`, default logic
        allows only user who owns the file to perform any operation on it. It
        means, that nobody is allowed to do anything with file owner by
        resource, dataset, group, etc.

        Example:
        >>> def files_is_allowed(self, context, file, operation) -> bool | None:
        >>>     if file.owner_info and file.owner_info == "resource"
        >>>         return is_authorized_boolean(
        >>>             f"resource_{operation}",
        >>>             context,
        >>>             {"id": file.owner_info.id}
        >>>         )
        >>>
        >>>     return None

        """
        return None
