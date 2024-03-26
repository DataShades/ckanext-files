import os

import ckan.plugins.toolkit as tk

from ckanext.files.utils import make_collector

_helpers, helper = make_collector()

HERE = os.path.dirname(__file__)


def get_helpers():
    return dict(_helpers)


@helper
def files_humanize_content_type(content_type):
    # type: (str) -> str
    if not content_type:
        content_type = "application/octet-stream"

    # for name, types in tk.h.resource_formats().items():
    #     if name == content_type or content_type in types:
    #         return types[2]

    main, _sub = content_type.split("/")
    return main.capitalize()


@helper
def files_content_type_icon(content_type, theme, extension):
    # type: (str, str, str) -> str | None
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
