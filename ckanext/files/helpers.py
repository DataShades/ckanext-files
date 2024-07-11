from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Iterable, TypedDict

import ckan.plugins.toolkit as tk
from ckan import model

from . import shared

HERE = os.path.dirname(__file__)


class LinkDetails(TypedDict):
    label: str
    content_type: str
    size: int
    href: str | None


def files_parse_tz_date(value: str, strip_timezone: bool = False):
    """Transform timezone-aware ISO 8601 value into datetime object."""
    result = datetime.fromisoformat(value)
    if strip_timezone:
        result = result.replace(tzinfo=None)

    return result


def files_humanize_content_type(content_type: str) -> str:
    if not content_type:
        content_type = "application/octet-stream"

    # for name, types in tk.h.resource_formats().items():
    #     if name == content_type or content_type in types:
    #         return types[2]

    main, _sub = content_type.split("/")
    return main.capitalize()


def files_content_type_icon(
    content_type: str,
    theme: str,
    extension: str,
) -> str | None:
    if not content_type:
        content_type = "application/octet-stream"

    url = "ckanext-files/mimetype_icons/{}/{}.{}".format(
        theme,
        content_type.replace("/", "-"),
        extension,
    )

    if os.path.exists(os.path.join(HERE, "public", url)):
        return tk.h.url_for_static(url)

    return None


def files_get_file(file_id: str) -> shared.File | None:
    return model.Session.get(shared.File, file_id)


def files_link_details(
    file_id: str,
    *types: Iterable[str],
    **kwargs: Any,
) -> LinkDetails | None:
    file = model.Session.get(shared.File, file_id)

    if not file:
        return None

    storage = shared.get_storage(file.storage)

    for lt in types or ("public", "temporal"):
        func = getattr(storage, f"{lt}_link", None)
        if not func:
            continue
        if link := func(shared.FileData.from_model(file), **kwargs):
            return {
                "label": file.name,
                "content_type": file.content_type,
                "size": file.size,
                "href": link,
            }


def _is_storage_configured(name: str) -> bool:
    try:
        return bool(shared.get_storage(name))
    except shared.exc.UnknownStorageError:
        return False


def files_group_images_storage_is_configured() -> bool:
    return _is_storage_configured(shared.config.group_images_storage())


def files_user_images_storage_is_configured() -> bool:
    return _is_storage_configured(shared.config.user_images_storage())


def files_resources_storage_is_configured() -> bool:
    return _is_storage_configured(shared.config.resources_storage())
