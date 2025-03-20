from __future__ import annotations

import dataclasses

from file_keeper.default.adapters import redis as rd

import ckan.plugins.toolkit as tk
from ckan.config.declaration import Declaration, Key

from ckanext.files import shared


def _default_prefix():
    return "ckanext:files:{}:file_content".format(tk.config["ckan.site_id"])


@dataclasses.dataclass()
class Settings(shared.Settings, rd.Settings):
    pass


class RedisStorage(shared.Storage, rd.RedisStorage):
    settings: Settings  # type: ignore
    SettingsFactory = Settings

    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        super().declare_config_options(declaration, key)
        declaration.declare(key.path, _default_prefix()).set_description(
            "Name of the Redis key for HASH with files.",
        )
        declaration.declare(key.redis_url).set_description(
            "Static prefix of the Redis key generated for every upload.",
        ).append_validators("configured_default('ckan.redis.url',None)")
