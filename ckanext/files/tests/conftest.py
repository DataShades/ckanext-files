from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any, cast
from unittest import mock as _mock

import pytest
import pytz
from freezegun import freeze_time
from responses import RequestsMock
from werkzeug.datastructures import FileStorage

from ckan.lib.redis import connect_to_redis
from ckan.tests.helpers import call_action

call_action: Any


@pytest.fixture()
def mock():
    return _mock


@pytest.fixture()
def responses(ckan_config: dict[str, Any]):
    with RequestsMock() as rsps:
        rsps.add_passthru(ckan_config["solr_url"])
        yield rsps


@pytest.fixture()
def files_stopped_time():
    now = datetime.now(pytz.utc)
    with freeze_time(now):
        yield now


@pytest.fixture()
def clean_db(reset_db: Any, migrate_db_for: Any):
    # fix for CKAN v2.9 issue with `reset_db` attempting to remove all
    # registered models, not only core-models
    migrate_db_for("files")
    reset_db()
    migrate_db_for("files")


class FakeFileStorage(FileStorage):
    def __init__(self, stream: Any, filename: str):
        self.filename = filename

        super().__init__(stream, filename, "upload")


@pytest.fixture()
def create_with_upload(ckan_config: dict[str, Any], monkeypatch: Any, tmpdir: Any):
    """Reimplementation of original CKAN fixture with better fake storage.

    CKAN version adds just a few attributes to FileStorage object, while
    current plugin requires exact immitation.
    """
    from ckan.lib import uploader

    storage_path = str(tmpdir)
    monkeypatch.setitem(ckan_config, "ckan.storage_path", storage_path)
    if hasattr(uploader, "_storage_path"):
        monkeypatch.setattr(uploader, "_storage_path", storage_path)

    def factory(data: Any, filename: str, context: Any = None, **kwargs: Any):
        if context is None:
            context = {}

        action = kwargs.pop("action", "resource_create")
        field = kwargs.pop("upload_field_name", "upload")
        test_file = BytesIO()
        if isinstance(data, str):
            data = data.encode()
        test_file.write(data)
        test_file.seek(0)
        test_resource = FakeFileStorage(test_file, filename)

        params = {
            field: test_resource,
        }
        params.update(kwargs)
        return call_action(action, context, **params)

    return factory


@pytest.fixture(scope="session")
def reset_redis():
    def cleaner(pattern: str = "*"):
        """Remove keys matching pattern.

        Return number of removed records.
        """
        conn = connect_to_redis()
        keys = cast(Any, conn.keys(pattern))
        if keys:
            return cast(int, conn.delete(*keys))
        return 0

    return cleaner


@pytest.fixture()
def clean_redis(reset_redis: Any):
    """Remove all keys from Redis.

    This fixture removes all the records from Redis.

    Example:
        ```python
        @pytest.mark.usefixtures("clean_redis")
        def test_redis_is_empty():
            assert redis.keys("*") == []
        ```

    If test requires presence of some initial data in redis, make sure that
    data producer applied **after** ``clean_redis``:

    Example:
        ```python
        @pytest.mark.usefixtures(
            "clean_redis",
            "fixture_that_adds_xxx_key_to_redis"
        )
        def test_redis_has_one_record():
            assert redis.keys("*") == [b"xxx"]
        ```
    """
    reset_redis()
