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


def fuw_truncate_file_name(file_name: str, max_length=35) -> str:
    """Truncate file name if it is longer than the maximum length.

    Args:
        file_name (str): File name
        max_length (int, optional): Maximum length of the file name. Defaults to 35.

    Returns:
        str: truncated file name
    """
    if len(file_name) <= max_length:
        return file_name

    keep_length = (max_length - 3) // 2
    start = file_name[:keep_length]
    end = file_name[-keep_length:]

    return f"{start}...{end}"
