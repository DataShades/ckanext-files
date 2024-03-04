import hashlib
import uuid

import six

import ckan.plugins.toolkit as tk
from ckan.lib.redis import connect_to_redis

from ckanext.files import utils

from .base import Capability, Manager, Storage, Uploader

if six.PY3:
    from typing import Any  # isort: skip
    from werkzeug.datastructures import FileStorage  # isort: skip
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

        filename = str(uuid.uuid4())
        key = self.storage.settings["prefix"] + filename

        md5 = hashlib.md5()
        content = upload.stream.read()
        md5.update(content)

        self.storage.redis.set(key, content)

        return {
            "filename": filename,
            "content_type": upload.content_type,
            "size": len(content),
            "hash": md5.hexdigest(),
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
            "prefix", "ckanext:files:{}:file_content:".format(tk.config["ckan.site_id"])
        )
        super(RedisStorage, self).__init__(**settings)
        self.redis = connect_to_redis()
