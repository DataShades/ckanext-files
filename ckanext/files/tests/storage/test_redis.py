import hashlib
from io import BytesIO
from typing import Any
from uuid import UUID

import pytest
from werkzeug.datastructures import FileStorage

from ckanext.files import exceptions
from ckanext.files.storage import redis

from faker import Faker  # isort: skip # noqa: F401


@pytest.fixture()
def storage(clean_redis: Any):
    return redis.RedisStorage(name="test")


class TestUploader:
    def test_key(self, storage: redis.RedisStorage):
        # type: (redis.RedisStorage) -> None
        result = storage.upload("", FileStorage(), {})

        assert UUID(result.location)
        assert result.size == 0

        key = storage.settings["prefix"] + result.location
        assert storage.redis.get(key) == b""

    def test_content(self, storage: redis.RedisStorage, faker):
        # type: (redis.RedisStorage, Faker) -> None
        content = faker.binary(100)
        result = storage.upload("", FileStorage(BytesIO(content)), {})

        assert result.size == 100

        key = storage.settings["prefix"] + result.location
        assert storage.redis.get(key) == content

    def test_hash(self, storage: redis.RedisStorage, faker):
        # type: (redis.RedisStorage, Faker) -> None
        result = storage.upload("", FileStorage(), {})
        assert result.hash == hashlib.md5().hexdigest()

        content = faker.binary(100)
        result = storage.upload("", FileStorage(BytesIO(content)), {})
        assert result.hash == hashlib.md5(content).hexdigest()

    def test_copy(self, storage: redis.RedisStorage, faker):
        # type: (redis.RedisStorage, Faker) -> None
        content = faker.binary(100)
        original = storage.upload("", FileStorage(BytesIO(content)), {})
        copy = storage.copy(original, storage, faker.file_name(), {})

        assert copy.location != original.location
        assert storage.content(copy) == storage.content(original)

    def test_move(self, storage: redis.RedisStorage, faker):
        # type: (redis.RedisStorage, Faker) -> None
        content = faker.binary(100)
        original = storage.upload("", FileStorage(BytesIO(content)), {})
        copy = storage.move(original, storage, faker.file_name(), {})

        with pytest.raises(exceptions.MissingFileError):
            storage.content(original)

        assert storage.content(copy) == content


class TestManager:
    def test_removal(self, storage: redis.RedisStorage):
        # type: (redis.RedisStorage) -> None
        result = storage.upload("", FileStorage(), {})
        key = storage.settings["prefix"] + result.location

        assert storage.redis.exists(key)

        storage.remove(result)
        assert not storage.redis.exists(key)

    def test_exists(self, storage: redis.RedisStorage):
        # type: (redis.RedisStorage) -> None
        result = storage.upload("", FileStorage(), {})

        assert storage.exists(result)
        storage.remove(result)
        assert not storage.exists(result)


class TestReader:
    def test_stream(self, storage: redis.RedisStorage, faker):
        # type: (redis.RedisStorage, Faker) -> None
        data = faker.binary(100)
        result = storage.upload("", FileStorage(BytesIO(data)), {})

        stream = storage.stream(result)

        assert stream.read() == data

    def test_content(self, storage: redis.RedisStorage, faker):
        # type: (redis.RedisStorage, Faker) -> None
        data = faker.binary(100)
        result = storage.upload("", FileStorage(BytesIO(data)), {})

        content = storage.content(result)

        assert content == data

    def test_missing(self, storage: redis.RedisStorage, faker):
        # type: (redis.RedisStorage, Faker) -> None
        result = storage.upload("", FileStorage(), {})
        result.location += faker.uuid4()

        with pytest.raises(exceptions.MissingFileError):
            storage.stream(result)

        with pytest.raises(exceptions.MissingFileError):
            storage.content(result)
