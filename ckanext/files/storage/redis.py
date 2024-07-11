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
from ckanext.files.utils import IterableBytesReader

connect_to_redis: Any


class RedisUploader(Uploader):
    storage: RedisStorage

    required_options = ["prefix"]
    capabilities = Capability.CREATE | Capability.MULTIPART

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

    def multipart_start(
        self,
        location: str,
        data: MultipartData,
        extras: dict[str, Any],
    ) -> MultipartData:
        """Prepare everything for multipart(resumable) upload."""
        safe_location = self.storage.compute_location(location)
        key = self.storage.settings["prefix"] + safe_location
        self.storage.redis.set(key, b"")
        data.location = safe_location
        data.storage_data["uploaded"] = 0
        return data

    def multipart_refresh(
        self,
        data: MultipartData,
        extras: dict[str, Any],
    ) -> MultipartData:
        """Show details of the incomplete upload."""
        return data

    def multipart_update(
        self,
        data: MultipartData,
        extras: dict[str, Any],
    ) -> MultipartData:
        """Add data to the incomplete upload."""
        data = copy.deepcopy(data)
        schema = {
            "upload": [
                tk.get_validator("not_missing"),
                tk.get_validator("files_into_upload"),
            ],
            "__extras": [tk.get_validator("ignore")],
        }
        valid_extras, errors = tk.navl_validate(extras, schema)

        if errors:
            raise tk.ValidationError(errors)

        key = self.storage.settings["prefix"] + data.location
        size = cast(int, self.storage.redis.strlen(key))

        upload: Upload = valid_extras["upload"]
        expected_size = size + upload.size
        if expected_size > data.size:
            raise exceptions.UploadOutOfBoundError(expected_size, data.size)

        self.storage.redis.append(key, upload.stream.read())
        data.storage_data["uploaded"] = expected_size
        return data

    def multipart_complete(
        self,
        data: MultipartData,
        extras: dict[str, Any],
    ) -> FileData:
        """Verify file integrity and finalize incomplete upload."""
        key = self.storage.settings["prefix"] + data.location
        size = cast(int, self.storage.redis.strlen(key))

        if size != data.size:
            raise exceptions.UploadSizeMismatchError(size, data.size)

        reader = HashingReader(
            IterableBytesReader(self.storage.stream(FileData(data.location))),
        )

        content_type = magic.from_buffer(next(reader, b""), True)
        if data.content_type and content_type != data.content_type:
            raise exceptions.UploadTypeMismatchError(
                content_type,
                data.content_type,
            )
        reader.exhaust()

        if data.hash and data.hash != reader.get_hash():
            raise exceptions.UploadHashMismatchError(reader.get_hash(), data.hash)

        return FileData(data.location, size, content_type, reader.get_hash())


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
            size=cast(int, self.storage.redis.strlen(key)),
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

        if (
            self.storage.redis.exists(dest)
            and not self.storage.settings["override_existing"]
        ):
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

        if (
            self.storage.redis.exists(dest)
            and not self.storage.settings["override_existing"]
        ):
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

    @classmethod
    def prepare_settings(cls, settings: dict[str, Any]):
        settings.setdefault("prefix", _default_prefix())
        return super().prepare_settings(settings)

    def __init__(self, settings: Any):
        self.redis: redis.Redis = connect_to_redis()
        super().__init__(settings)

    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        super().declare_config_options(declaration, key)
        declaration.declare(key.prefix, _default_prefix()).set_description(
            "Static prefix of the Redis key generated for every upload.",
        )


def _default_prefix():
    return "ckanext:files:{}:file_content:".format(tk.config["ckan.site_id"])
