import six

if six.PY3:
    from typing import Any  # isort: skip # noqa: F401


from ckan.plugins import Interface


class IFiles(Interface):
    def files_get_storage_adapters(self):
        # type: () -> dict[str, Any]
        return {}
