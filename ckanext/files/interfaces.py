"""Interfaces of the extension."""

from __future__ import annotations

from typing import Any, Callable

from ckan.plugins import Interface

from ckanext.files import types

File = Multipart = Any


# --8<-- [start:interface]
class IFiles(Interface):
    """Extension point for ckanext-files.

    This interface is not stabilized. Implement it with `inherit=True`.

    Example:
        ```python
        class MyPlugin(p.SingletonPlugin):
            p.implements(interfaces.IFiles, inherit=True)
        ```
    """

    def files_get_storage_adapters(self) -> dict[str, Any]:
        """Return mapping of storage type to adapter class.

        Returns:
            adapters provided by the implementation

        Example:
            ```python
            def files_get_storage_adapters(self):
                return {
                    "my_ext:dropbox": DropboxStorage,
                }
            ```
        """
        return {}

    def files_register_owner_getters(self) -> dict[str, Callable[[str], Any]]:
        """Return mapping with lookup functions for owner types.

        Name of the getter is the name used as `Owner.owner_type`. The getter
        itself is a function that accepts owner ID and returns optional owner
        entity.

        Returns:
            getters for specific owner types

        Example:
            ```python
            def files_register_owner_getters(self):
                return {"resource": model.Resource.get}
            ```
        """
        return {}

    def files_file_allows(
        self,
        context: types.Context,
        file: File | Multipart,
        operation: types.FileOperation,
    ) -> bool | None:
        """Decide if user is allowed to perform specified operation on the file.

        Return True/False if user allowed/not allowed. Return `None` to rely on
        other plugins.

        Default implementation relies on cascade_access config option. If owner
        of file is included into cascade access, user can perform operation on
        file if he can perform the same operation with file's owner.

        If current owner is not affected by cascade access, user can perform
        operation on file only if user owns the file.

        Args:
            context: API context
            file: accessed file object
            operation: performed operation

        Returns:
            decision whether operation is allowed for the file

        Example:
            ```python
            def files_file_allows(
                    self, context,
                    file: shared.File | shared.Multipart,
                    operation: shared.types.FileOperation
            ) -> bool | None:
                if file.owner_info and file.owner_info.owner_type == "resource":
                    return is_authorized_boolean(
                        f"resource_{operation}",
                        context,
                        {"id": file.owner_info.id}
                    )

                return None
            ```
        """
        return None

    def files_owner_allows(
        self,
        context: types.Context,
        owner_type: str,
        owner_id: str,
        operation: types.OwnerOperation,
    ) -> bool | None:
        """Decide if user is allowed to perform specified operation on the owner.

        Return True/False if user allowed/not allowed. Return `None` to rely on
        other plugins.

        Args:
            context: API context
            owner_type: type of the tested owner
            owner_id: type of the tested owner
            operation: performed operation

        Returns:
            decision whether operation is allowed for the owner

        Example:
            ```python
            def files_owner_allows(
                    self, context,
                    owner_type: str, owner_id: str,
                    operation: shared.types.OwnerOperation
            ) -> bool | None:
                if owner_type == "resource" and operation == "file_transfer":
                    return is_authorized_boolean(
                        f"resource_update",
                        context,
                        {"id": owner_id}
                    )

                return None
            ```
        """
        return None


# --8<-- [start:interface]
