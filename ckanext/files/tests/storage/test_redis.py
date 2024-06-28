import hashlib
from io import BytesIO
from typing import Any
from uuid import UUID

import pytest
from faker import Faker

from ckanext.files import exceptions, shared
from ckanext.files.storage import redis


@pytest.fixture()
def storage(clean_redis: Any):
    return redis.RedisStorage(redis.RedisStorage.prepare_settings({"name": "test"}))


class TestUploader:
    def test_key(self, storage: redis.RedisStorage):
        result = storage.upload("", shared.make_upload(b""))

        assert UUID(result.location)
        assert result.size == 0

        key = storage.settings["prefix"] + result.location
        assert storage.redis.get(key) == b""

    def test_content(self, storage: redis.RedisStorage, faker: Faker):
        content = faker.binary(100)
        result = storage.upload("", shared.make_upload(BytesIO(content)))

        assert result.size == 100

        key = storage.settings["prefix"] + result.location
        assert storage.redis.get(key) == content

    def test_hash(self, storage: redis.RedisStorage, faker: Faker):
        result = storage.upload("", shared.make_upload(b""))
        assert result.hash == hashlib.md5().hexdigest()

        content = faker.binary(100)
        result = storage.upload("", shared.make_upload(BytesIO(content)))
        assert result.hash == hashlib.md5(content).hexdigest()

    def test_copy(self, storage: redis.RedisStorage, faker: Faker):
        content = faker.binary(100)
        original = storage.upload("", shared.make_upload(BytesIO(content)))
        copy = storage.copy(original, storage, faker.file_name())

        assert copy.location != original.location
        assert storage.content(copy) == storage.content(original)

    def test_move(self, storage: redis.RedisStorage, faker: Faker):
        content = faker.binary(100)
        original = storage.upload("", shared.make_upload(BytesIO(content)))
        copy = storage.move(original, storage, faker.file_name())

        with pytest.raises(exceptions.MissingFileError):
            storage.content(original)

        assert storage.content(copy) == content


class TestManager:
    def test_removal(self, storage: redis.RedisStorage):
        result = storage.upload("", shared.make_upload(b""))
        key = storage.settings["prefix"] + result.location

        assert storage.redis.exists(key)

        storage.remove(result)
        assert not storage.redis.exists(key)

    def test_exists(self, storage: redis.RedisStorage):
        result = storage.upload("", shared.make_upload(b""))

        assert storage.exists(result)
        storage.remove(result)
        assert not storage.exists(result)


class TestReader:
    def test_stream(self, storage: redis.RedisStorage, faker: Faker):
        data = faker.binary(100)
        result = storage.upload("", shared.make_upload(BytesIO(data)))

        stream = storage.stream(result)

        assert b"".join(stream) == data

    def test_content(self, storage: redis.RedisStorage, faker: Faker):
        data = faker.binary(100)
        result = storage.upload("", shared.make_upload(BytesIO(data)))

        content = storage.content(result)

        assert content == data

    def test_missing(self, storage: redis.RedisStorage, faker: Faker):
        result = storage.upload("", shared.make_upload(b""))
        result.location += str(faker.uuid4())

        with pytest.raises(exceptions.MissingFileError):
            storage.stream(result)

        with pytest.raises(exceptions.MissingFileError):
            storage.content(result)
