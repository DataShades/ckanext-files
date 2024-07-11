"""Configuration readers of the extension.

This module contains functions that simplify accessing configuration option
from the CKAN config file.

It's recommended to use these functions istead of accessing config options by
name, if you want your code to be more compatible with different versions of
the extension.

"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import ckan.plugins.toolkit as tk

STORAGE_PREFIX = "ckanext.files.storage."
DEFAULT_STORAGE = "ckanext.files.default_storage"
CASCADE_ACCESS = "ckanext.files.owner.cascade_access"
TRANSFER_AS_UPDATE = "ckanext.files.owner.transfer_as_update"
SCAN_AS_UPDATE = "ckanext.files.owner.scan_as_update"
AUTHENTICATED_UPLOADS = "ckanext.files.authenticated_uploads.allow"
AUTHENTICATED_STORAGES = "ckanext.files.authenticated_uploads.storages"
USER_IMAGES_STORAGE = "ckanext.files.user_images_storage"
GROUP_IMAGES_STORAGE = "ckanext.files.group_images_storage"
RESOURCE_STORAGE = "ckanext.files.resources_storage"
ENABLE_RESOURCE_HACK = "ckanext.files.enable_resource_migration_template_patch"
INLINE_TYPES = "ckanext.files.inline_content_types"


def default_storage() -> str:
    """Default storage used for upload when no explicit storage specified."""
    return tk.config[DEFAULT_STORAGE]


def storages() -> dict[str, dict[str, Any]]:
    """Mapping of storage names to their settings."""
    storages = defaultdict(dict)  # type: dict[str, dict[str, Any]]
    prefix_len = len(STORAGE_PREFIX)
    for k, v in tk.config.items():
        if not k.startswith(STORAGE_PREFIX):
            continue

        try:
            name, option = k[prefix_len:].split(".", 1)
        except ValueError:
            continue

        storages[name][option] = v
    return storages


def cascade_access() -> list[str]:
    """List of owner types that grant automatic access on owned file."""
    return tk.config[CASCADE_ACCESS]


def authenticated_uploads() -> bool:
    """Any authenticated user can upload files."""
    return tk.config[AUTHENTICATED_UPLOADS]


def transfer_as_update() -> bool:
    """Use `*_update` auth when transfering ownership."""
    return tk.config[TRANSFER_AS_UPDATE]


def scan_as_update() -> bool:
    """Use `*_update` auth when listing files of the owner."""
    return tk.config[SCAN_AS_UPDATE]


def authenticated_storages() -> list[str]:
    """Names of storages that can by used by non-sysadmins."""
    return tk.config[AUTHENTICATED_STORAGES]


def group_images_storage() -> str:
    """Storage used for group image uploads."""
    return tk.config[GROUP_IMAGES_STORAGE]


def user_images_storage() -> str:
    """Storage used for user image uploads."""
    return tk.config[USER_IMAGES_STORAGE]


def resources_storage() -> str:
    """Storage used for resource uploads."""
    return tk.config[RESOURCE_STORAGE]


def override_resource_form() -> bool:
    return tk.config[ENABLE_RESOURCE_HACK]


def inline_types() -> list[str]:
    return tk.config[INLINE_TYPES]
