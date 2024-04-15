from io import BytesIO

import ckan.plugins.toolkit as tk
from ckan.lib.redis import connect_to_redis  # type: ignore

from ckanext.files import exceptions, types, utils
from ckanext.files.base import (
    Capability,
    HashingReader,
    Manager,
    Reader,
    Storage,
    Uploader,
)

import redis  # isort: skip # noqa: F401


RedisAdditionalData = types.TypedDict("RedisAdditionalData", {})


class RedisStorageData(RedisAdditionalData, types.MinimalStorageData):
    pass


class RedisUploader(Uploader):
    storage = None  # type: RedisStorage # pyright: ignore

    required_options = ["prefix"]
    capabilities = utils.combine_capabilities(
        Capability.CREATE,
        Capability.COPY,
        Capability.MOVE,
    )

    def upload(self, name, upload, extras):
        # type: (str, types.Upload, dict[str, types.Any]) -> RedisStorageData

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
    storage = None  # type: RedisStorage # pyright: ignore

    required_options = ["prefix"]
    capabilities = utils.combine_capabilities(Capability.STREAM)

    def stream(self, data):
        # type: (dict[str, types.Any]) -> types.IO[bytes]
        return BytesIO(self.content(data))

    def content(self, data):
        # type: (dict[str, types.Any]) -> bytes
        key = self.storage.settings["prefix"] + data["filename"]
        value = self.storage.redis.get(key)
        if value is None:
            raise exceptions.MissingFileError(self.storage.settings["name"], key)

        return value


class RedisManager(Manager):
    storage = None  # type: RedisStorage # pyright: ignore

    required_options = ["prefix"]
    capabilities = utils.combine_capabilities(Capability.REMOVE, Capability.EXISTS)

    def remove(self, data):
        # type: (RedisStorageData) -> bool
        key = self.storage.settings["prefix"] + data["filename"]
        self.storage.redis.delete(key)
        return True

    def exists(self, data):
        # type: (RedisStorageData) -> bool
        key = self.storage.settings["prefix"] + data["filename"]
        return bool(self.storage.redis.exists(key))

    def copy(self, data, name, extras):
        # type: (types.MinimalStorageData, str, dict[str, types.Any]) -> RedisStorageData
        src = self.storage.settings["prefix"] + data["filename"]
        dest = self.storage.settings["prefix"] + name

        if not self.storage.redis.exists(src):
            raise exceptions.MissingFileError(self.storage.settings["name"], src)

        if self.storage.redis.exists(dest):
            raise exceptions.ExistingFileError(self.storage.settings["name"], dest)

        try:
            self.storage.redis.copy(src, dest)
        except AttributeError:
            self.storage.redis.restore(dest, 0, self.storage.redis.dump(src))

        return RedisStorageData(data, filename=name)

    def move(self, data, name, extras):
        # type: (types.MinimalStorageData, str, dict[str, types.Any]) -> RedisStorageData
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

    def __init__(self, **settings):
        # type: (**types.Any) -> None

        settings.setdefault(
            "prefix",
            _default_prefix(),
        )
        super(RedisStorage, self).__init__(**settings)
        self.redis = connect_to_redis()  # type: redis.Redis[bytes]

    @classmethod
    def declare_config_options(cls, declaration, key):
        # type: (types.Declaration, types.Key) -> None
        super().declare_config_options(declaration, key)
        declaration.declare(key.prefix, _default_prefix()).set_description(
            "Static prefix of the Redis key generated for every upload.",
        )


def _default_prefix():
    return "ckanext:files:{}:file_content:".format(tk.config["ckan.site_id"])
