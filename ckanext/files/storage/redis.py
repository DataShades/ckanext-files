import six

import ckan.plugins.toolkit as tk
from ckan.lib.redis import connect_to_redis

from ckanext.files import utils

from .base import Capability, HashingReader, Manager, Storage, Uploader

if six.PY3:
    from typing import Any  # isort: skip # noqa: F401
    from werkzeug.datastructures import FileStorage  # isort: skip # noqa: F401
    from typing_extensions import TypedDict

    from .base import MinimalStorageData

    RedisAdditionalData = TypedDict("RedisAdditionalData", {"filename": str})

    class RedisStorageData(RedisAdditionalData, MinimalStorageData):
        pass


class RedisUploader(Uploader):
    storage = None  # type: RedisStorage # pyright: ignore

    required_options = ["prefix"]
    capabilities = utils.combine_capabilities(Capability.CREATE)

    def upload(self, name, upload, extras):  # pragma: no cover
        # type: (str, FileStorage, dict[str, Any]) -> RedisStorageData

        filename = self.compute_name(name, extras, upload)
        key = self.storage.settings["prefix"] + filename

        reader = HashingReader(upload.stream)
        for chunk in reader:
            self.storage.redis.append(key, chunk)

        return {
            "filename": filename,
            "content_type": upload.content_type,
            "size": reader.position,
            "hash": reader.get_hash(),
        }


class RedisManager(Manager):
    storage = None  # type: RedisStorage # pyright: ignore

    required_options = ["prefix"]
    capabilities = utils.combine_capabilities(Capability.REMOVE)

    def remove(self, data):
        # type: (dict[str, Any]) -> bool
        key = self.storage.settings["prefix"] + data["filename"]
        self.storage.redis.delete(key)
        return True


class RedisStorage(Storage):
    def make_uploader(self):
        return RedisUploader(self)

    def make_manager(self):
        return RedisManager(self)

    def __init__(self, **settings):
        # type: (**Any) -> None

        settings.setdefault(
            "prefix",
            "ckanext:files:{}:file_content:".format(tk.config["ckan.site_id"]),
        )
        super(RedisStorage, self).__init__(**settings)
        self.redis = connect_to_redis()
