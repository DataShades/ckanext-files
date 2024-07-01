from __future__ import annotations

import math
from typing import Any

import ckan.plugins.toolkit as tk


def fuw_get_user_files(user: str) -> list[dict[str, Any]]:
    return tk.get_action("files_file_scan")({}, {}).get("results", [])


def fuw_printable_file_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return "0 bytes"

    size_name = ("bytes", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(float(size_bytes) / p, 1)

    return "%s %s" % (s, size_name[i])
