"""Interfaces of the extension.
"""

import six

if six.PY3:
    from typing import Any  # isort: skip # noqa: F401


from ckan.plugins import Interface


class IFiles(Interface):
    """Extension point for ckanext-files."""

    def files_get_storage_adapters(self):
        # type: () -> dict[str, Any]
        """Return mapping of storage type to storage factory.

        Example:
        >>> def files_get_storage_adapters(self):
        >>>     return {
        >>>         "my_ext:dropbox": DropboxStorage,
        >>>     }

        """

        return {}
