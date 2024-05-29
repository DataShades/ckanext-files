"""Interfaces of the extension.
"""

from __future__ import annotations

from typing import Any

from ckan.plugins import Interface


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
