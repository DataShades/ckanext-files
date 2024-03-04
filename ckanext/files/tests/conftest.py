from __future__ import annotations

from io import BytesIO

import pytest
import six
from werkzeug.datastructures import FileStorage

from ckan.tests.helpers import call_action

if six.PY3:
    from typing import Any  # isort: skip


@pytest.fixture
def clean_db(reset_db, migrate_db_for):
    # type: (Any, Any) -> None
    reset_db()
    migrate_db_for("files")


class FakeFileStorage(FileStorage):
    def __init__(self, stream, filename):
        # type: (Any, str) -> None
        super(FakeFileStorage, self).__init__(stream, filename, "uplod")


@pytest.fixture
def create_with_upload(ckan_config, monkeypatch, tmpdir):
    # type: (Any, Any, Any) -> Any
    """Reimplementation of original CKAN fixture with better fake storage.

    CKAN version adds just a few attributes to FileStorage object, while
    current plugin requires exact immitation.
    """

    monkeypatch.setitem(ckan_config, "ckan.storage_path", str(tmpdir))

    def factory(data, filename, context=None, **kwargs):
        # type: (Any, Any, Any, **Any) -> Any
        if context is None:
            context = {}

        action = kwargs.pop("action", "resource_create")
        field = kwargs.pop("upload_field_name", "upload")
        test_file = BytesIO()
        if not isinstance(data, bytes):
            data = bytes(data, encoding="utf-8")
        test_file.write(data)
        test_file.seek(0)
        test_resource = FakeFileStorage(test_file, filename)

        params = {
            field: test_resource,
        }
        params.update(kwargs)
        return call_action(action, context, **params)

    return factory
