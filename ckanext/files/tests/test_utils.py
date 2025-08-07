from __future__ import annotations

from collections.abc import Iterable

import pytest

from ckanext.files import utils


@pytest.mark.parametrize(
    ("type", "supported", "outcome"),
    [
        ("text/csv", ["csv"], True),
        ("text/csv", ["json", "text"], True),
        ("text/csv", ["application/json", "text/plain", "text/csv", "image/png"], True),
        ("text/csv", ["json", "image"], False),
        ("text/csv", ["application/csv"], False),
        ("text/csv", ["text/plain"], False),
        ("text/csv", ["non-csv"], False),
    ],
)
def test_is_supported_type(type: str, supported: Iterable[str], outcome: bool):
    assert utils.is_supported_type(type, supported) is outcome
