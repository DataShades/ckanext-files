from __future__ import annotations

import dataclasses
from typing import Any

from file_keeper.default.adapters import libcloud as lc

from ckan.config.declaration import Declaration, Key

from ckanext.files import shared

PROVIDERS_URL = (
    "https://libcloud.readthedocs.io/en/stable/storage/"
    + "supported_providers.html#provider-matrix"
)

get_driver: Any


@dataclasses.dataclass()
class Settings(shared.Settings, lc.Settings):
    pass


class LibCloudStorage(shared.Storage, lc.LibCloudStorage):
    settings: Settings  # type: ignore
    SettingsFactory = Settings

    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        super().declare_config_options(declaration, key)
        declaration.declare(key.provider).required().set_description(
            "apache-libcloud storage provider. List of providers available at"
            + f" {PROVIDERS_URL} . Use upper-cased value from Provider Constant column",
        )
        declaration.declare(key.key).required().set_description("API key or username")
        declaration.declare(key.secret).set_description("Secret password")
        declaration.declare(key.container_name).required().set_description(
            "Name of the container(bucket)",
        )
        declaration.declare(key.params).set_description(
            "JSON object with additional parameters"
            + " passed directly to storage constructor.",
        ).set_validators("default({}) convert_to_json_if_string dict_only")
        declaration.declare(key.path).set_description(
            "Path inside the container where uploaded data will be stored.",
        )
