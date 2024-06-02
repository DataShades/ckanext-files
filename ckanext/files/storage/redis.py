from __future__ import annotations

import copy
from io import BytesIO
from typing import IO, Any, cast

import redis
from redis import ResponseError

import ckan.plugins.toolkit as tk
from ckan.config.declaration import Declaration, Key
from ckan.lib.redis import connect_to_redis

from ckanext.files import exceptions, types
from ckanext.files.base import HashingReader
from ckanext.files.shared import (
    Capability,
    FileData,
    Manager,
    Reader,
    Storage,
    Uploader,
)


class RedisUploader(Uploader):
    storage: RedisStorage

    required_options = ["prefix"]
    capabilities = Capability.combine(
        Capability.CREATE,
        Capability.COPY,
        Capability.MOVE,
    )

    def upload(
        self,
        location: str,
        upload: types.Upload,
        extras: dict[str, Any],
    ) -> FileData:
        safe_location = self.storage.compute_location(location, extras, upload)
        key = self.storage.settings["prefix"] + safe_location

        self.storage.redis.delete(key)

        reader = HashingReader(upload.stream)
        self.storage.redis.set(key, b"")
        for chunk in reader:
            self.storage.redis.append(key, chunk)

        return FileData(
            safe_location,
            reader.position,
            upload.content_type,
            reader.get_hash(),
        )


class RedisReader(Reader):
    storage: RedisStorage

    required_options = ["prefix"]
    capabilities = Capability.combine(Capability.STREAM)

    def stream(self, data: FileData) -> IO[bytes]:
        return BytesIO(self.content(data))

    def content(self, data: FileData) -> bytes:
        key = self.storage.settings["prefix"] + data.location
        value = cast("bytes | None", self.storage.redis.get(key))
        if value is None:
            raise exceptions.MissingFileError(self.storage.settings["name"], key)

        return value


class RedisManager(Manager):
    storage: RedisStorage

    required_options = ["prefix"]
    capabilities = Capability.combine(Capability.REMOVE, Capability.EXISTS)

    def remove(self, data: FileData) -> bool:
        key = self.storage.settings["prefix"] + data.location
        self.storage.redis.delete(key)
        return True

    def exists(self, data: FileData) -> bool:
        key = self.storage.settings["prefix"] + data.location
        return bool(self.storage.redis.exists(key))

    def copy(
        self,
        data: FileData,
        location: str,
        extras: dict[str, Any],
    ) -> FileData:
        safe_location = self.storage.compute_location(location, extras)
        src: str = self.storage.settings["prefix"] + data.location
        dest: str = self.storage.settings["prefix"] + safe_location

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

        new_data = copy.deepcopy(data)
        new_data.location = safe_location
        return new_data

    def move(
        self,
        data: FileData,
        location: str,
        extras: dict[str, Any],
    ) -> FileData:
        safe_location = self.storage.compute_location(location, extras)

        src = self.storage.settings["prefix"] + data.location
        dest = self.storage.settings["prefix"] + safe_location

        self.storage.redis.rename(src, dest)
        new_data = copy.deepcopy(data)
        new_data.location = safe_location
        return new_data


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
