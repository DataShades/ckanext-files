from __future__ import annotations

import copy
from io import BytesIO
from typing import IO, Any, Iterable, cast

import magic
import redis
from redis import ResponseError

import ckan.plugins.toolkit as tk
from ckan.config.declaration import Declaration, Key
from ckan.lib.redis import connect_to_redis

from ckanext.files import exceptions
from ckanext.files.shared import (
    Capability,
    FileData,
    HashingReader,
    Manager,
    MultipartData,
    Reader,
    Storage,
    Upload,
    Uploader,
)

connect_to_redis: Any


class RedisUploader(Uploader):
    storage: RedisStorage

    required_options = ["prefix"]
    capabilities = Capability.CREATE

    def upload(
        self,
        location: str,
        upload: Upload,
        extras: dict[str, Any],
    ) -> FileData:
        safe_location = self.storage.compute_location(location, upload, **extras)
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
    capabilities = Capability.STREAM

    def stream(self, data: FileData, extras: dict[str, Any]) -> IO[bytes]:
        return BytesIO(self.content(data, extras))

    def content(self, data: FileData, extras: dict[str, Any]) -> bytes:
        key = self.storage.settings["prefix"] + data.location
        value = cast("bytes | None", self.storage.redis.get(key))
        if value is None:
            raise exceptions.MissingFileError(self.storage, key)

        return value


class RedisManager(Manager):
    storage: RedisStorage

    required_options = ["prefix"]
    capabilities = (
        Capability.COPY
        | Capability.MOVE
        | Capability.REMOVE
        | Capability.EXISTS
        | Capability.SCAN
        | Capability.ANALYZE
    )

    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        prefix = self.storage.settings["prefix"]
        keys: Iterable[bytes] = self.storage.redis.scan_iter(f"{prefix}*")
        for key in keys:
            yield key.decode()[len(prefix) :]

    def analyze(self, location: str, extras: dict[str, Any]) -> FileData:
        """Return all details about location."""
        key = self.storage.settings["prefix"] + location
        value: Any = self.storage.redis.get(key)
        if value is None:
            raise exceptions.MissingFileError(self.storage, key)

        reader = HashingReader(BytesIO(value))
        content_type = magic.from_buffer(next(reader, b""), True)
        reader.exhaust()

        return FileData(
            location,
            size=cast(int, self.storage.redis.memory_usage(key)),
            content_type=content_type,
            hash=reader.get_hash(),
        )

    def remove(self, data: FileData | MultipartData, extras: dict[str, Any]) -> bool:
        key = self.storage.settings["prefix"] + data.location
        self.storage.redis.delete(key)
        return True

    def exists(self, data: FileData, extras: dict[str, Any]) -> bool:
        key = self.storage.settings["prefix"] + data.location
        return bool(self.storage.redis.exists(key))

    def copy(
        self,
        data: FileData,
        location: str,
        extras: dict[str, Any],
    ) -> FileData:
        safe_location = self.storage.compute_location(location, **extras)
        src: str = self.storage.settings["prefix"] + data.location
        dest: str = self.storage.settings["prefix"] + safe_location

        if not self.storage.redis.exists(src):
            raise exceptions.MissingFileError(self.storage, src)

        if self.storage.redis.exists(dest):
            raise exceptions.ExistingFileError(self.storage, dest)

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
        safe_location = self.storage.compute_location(location, **extras)

        src = self.storage.settings["prefix"] + data.location
        dest = self.storage.settings["prefix"] + safe_location

        if not self.storage.redis.exists(src):
            raise exceptions.MissingFileError(self.storage, src)

        if self.storage.redis.exists(dest):
            raise exceptions.ExistingFileError(self.storage, dest)

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
        self.redis: redis.Redis = connect_to_redis()
        super().__init__(**settings)

    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        super().declare_config_options(declaration, key)
        declaration.declare(key.prefix, _default_prefix()).set_description(
            "Static prefix of the Redis key generated for every upload.",
        )


def _default_prefix():
    return "ckanext:files:{}:file_content:".format(tk.config["ckan.site_id"])
