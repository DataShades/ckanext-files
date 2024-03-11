from io import BytesIO

import pytest
import six
from werkzeug.datastructures import FileStorage

from ckan.lib.redis import connect_to_redis
from ckan.tests.helpers import call_action
import ckan.plugins.toolkit as tk

if six.PY3:
    from typing import Any  # isort: skip # noqa: F401


if tk.check_ckan_version("2.9"):
    @pytest.fixture
    def clean_db(reset_db, migrate_db_for):
        # type: (Any, Any) -> None
        reset_db()
        migrate_db_for("files")

else:
    @pytest.fixture
    def clean_db(reset_db):
        # type: (Any) -> None
        from ckanext.files.command import create_tables, drop_tables
        reset_db()
        drop_tables()
        create_tables()




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
        if isinstance(data, six.text_type):
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
    def cleaner(pattern="*"):
        # type: (str) -> int
        """Remove keys matching pattern.
        Return number of removed records.
        """
        conn = connect_to_redis()
        keys = conn.keys(pattern)
        if keys:
            return conn.delete(*keys)
        return 0

    return cleaner


@pytest.fixture()
def clean_redis(reset_redis):
    """Remove all keys from Redis.
    This fixture removes all the records from Redis::
        @pytest.mark.usefixtures("clean_redis")
        def test_redis_is_empty():
            assert redis.keys("*") == []
    If test requires presence of some initial data in redis, make sure that
    data producer applied **after** ``clean_redis``::
        @pytest.mark.usefixtures(
            "clean_redis",
            "fixture_that_adds_xxx_key_to_redis"
        )
        def test_redis_has_one_record():
            assert redis.keys("*") == [b"xxx"]
    """
    reset_redis()
