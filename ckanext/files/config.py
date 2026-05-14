"""Configuration readers of the extension.

This module contains functions that simplify accessing configuration option
from the CKAN config file.

It's recommended to use these functions istead of accessing config options by
name, if you want your code to be more compatible with different versions of
the extension.

"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

import ckan.plugins.toolkit as tk

log = logging.getLogger(__name__)

if tk.check_ckan_version("2.12"):
    STORAGE_PREFIX = "ckan.files.storage."
    DEFAULT_STORAGE = "ckan.files.default_storages.default"
    CASCADE_ACCESS = "ckan.files.owner.cascade_access"
    TRANSFER_AS_UPDATE = "ckan.files.owner.transfer_as_update"
    SCAN_AS_UPDATE = "ckan.files.owner.scan_as_update"
    AUTHENTICATED_UPLOADS = "ckan.files.authenticated_uploads.allow"
    AUTHENTICATED_STORAGES = "ckan.files.authenticated_uploads.storages"
    USER_IMAGES_STORAGE = "ckan.files.default_storages.user"
    GROUP_IMAGES_STORAGE = "ckan.files.default_storages.group"
    RESOURCE_STORAGE = "ckan.files.default_storages.resource"
    INLINE_TYPES = "ckan.files.inline_content_types"

else:
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
    INLINE_TYPES = "ckanext.files.inline_content_types"

ENABLE_RESOURCE_HACK = "ckanext.files.enable_resource_migration_template_patch"


def default_storage() -> str:
    """Default storage used for upload when no explicit storage specified."""
    return tk.config[DEFAULT_STORAGE]


def storages() -> dict[str, dict[str, Any]]:
    """Mapping of storage names to their settings."""
    if tk.check_ckan_version("2.12"):
        from ckan.config.declaration.load import config_tree  # noqa: PLC0415

        return config_tree(tk.config, STORAGE_PREFIX, depth=-1)

    storages = defaultdict(dict)  # type: dict[str, dict[str, Any]]
    prefix_len = len(STORAGE_PREFIX)
    for k, v in tk.config.items():
        if not k.startswith(STORAGE_PREFIX):
            continue

        try:
            name, *path = k[prefix_len:].split(".")
        except ValueError:
            continue

        here: dict[str, Any] = storages[name]
        for segment in path[:-1]:
            here = here.setdefault(segment, {})
            if not isinstance(here, dict):  # pyright: ignore[reportUnnecessaryIsInstance]
                log.warning(
                    "Cannot build tree for %s at branch %s",
                    path,
                    segment,
                )
                break
        else:
            here[path[-1]] = v

    return storages


def cascade_access() -> dict[str, str]:
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
