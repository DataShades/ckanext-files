from __future__ import annotations

from io import BytesIO
from typing import IO, Any, cast

import redis
from redis import ResponseError
from typing_extensions import TypedDict

import ckan.plugins.toolkit as tk
from ckan.config.declaration import Declaration, Key
from ckan.lib.redis import connect_to_redis

from ckanext.files import exceptions, types
from ckanext.files.base import HashingReader
from ckanext.files.shared import Capability, Manager, Reader, Storage, Uploader

RedisAdditionalData = TypedDict("RedisAdditionalData", {})


class RedisStorageData(RedisAdditionalData, types.MinimalStorageData):
    pass


class RedisUploader(Uploader):
    storage: "RedisStorage"

    required_options = ["prefix"]
    capabilities = Capability.combine(
        Capability.CREATE,
        Capability.COPY,
        Capability.MOVE,
    )

    def upload(
        self,
        name: str,
        upload: types.Upload,
        extras: dict[str, Any],
    ) -> RedisStorageData:
        filename = self.storage.compute_name(name, extras, upload)
        key = self.storage.settings["prefix"] + filename

        self.storage.redis.delete(key)

        reader = HashingReader(upload.stream)
        self.storage.redis.set(key, b"")
        for chunk in reader:
            self.storage.redis.append(key, chunk)

        return {
            "filename": filename,
            "content_type": upload.content_type,
            "size": reader.position,
            "hash": reader.get_hash(),
        }


class RedisReader(Reader):
    storage: RedisStorage

    required_options = ["prefix"]
    capabilities = Capability.combine(Capability.STREAM)

    def stream(self, data: types.MinimalStorageData) -> IO[bytes]:
        return BytesIO(self.content(data))

    def content(self, data: types.MinimalStorageData) -> bytes:
        key = self.storage.settings["prefix"] + data["filename"]
        value = cast("bytes | None", self.storage.redis.get(key))
        if value is None:
            raise exceptions.MissingFileError(self.storage.settings["name"], key)

        return value


class RedisManager(Manager):
    storage: RedisStorage

    required_options = ["prefix"]
    capabilities = Capability.combine(Capability.REMOVE, Capability.EXISTS)

    def remove(self, data: RedisStorageData) -> bool:
        key = self.storage.settings["prefix"] + data["filename"]
        self.storage.redis.delete(key)
        return True

    def exists(self, data: RedisStorageData) -> bool:
        key = self.storage.settings["prefix"] + data["filename"]
        return bool(self.storage.redis.exists(key))

    def copy(
        self,
        data: types.MinimalStorageData,
        name: str,
        extras: dict[str, Any],
    ) -> RedisStorageData:
        src: str = self.storage.settings["prefix"] + data["filename"]
        dest: str = self.storage.settings["prefix"] + name

        if not self.storage.redis.exists(src):
            raise exceptions.MissingFileError(self.storage.settings["name"], src)

        if self.storage.redis.exists(dest):
            raise exceptions.ExistingFileError(self.storage.settings["name"], dest)

        try:
            self.storage.redis.copy(src, dest)
        except (AttributeError, ResponseError):
            self.storage.redis.restore(
                dest,
                0,
                cast(Any, self.storage.redis.dump(src)),
            )

        return RedisStorageData(data, filename=name)

    def move(
        self,
        data: types.MinimalStorageData,
        name: str,
        extras: dict[str, Any],
    ) -> RedisStorageData:
        filename = self.storage.compute_name(name, extras)

        src = self.storage.settings["prefix"] + data["filename"]
        dest = self.storage.settings["prefix"] + filename

        self.storage.redis.rename(src, dest)
        return RedisStorageData(data, filename=filename)


class RedisStorage(Storage):
    def make_uploader(self):
        return RedisUploader(self)

    def make_manager(self):
        return RedisManager(self)

    def make_reader(self):
        return RedisReader(self)

    def __init__(self, **settings: Any):
        settings.setdefault(
            "prefix",
            _default_prefix(),
        )
        super(RedisStorage, self).__init__(**settings)
        self.redis: redis.Redis = connect_to_redis()

    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        super().declare_config_options(declaration, key)
        declaration.declare(key.prefix, _default_prefix()).set_description(
            "Static prefix of the Redis key generated for every upload.",
        )


def _default_prefix():
    return "ckanext:files:{}:file_content:".format(tk.config["ckan.site_id"])
