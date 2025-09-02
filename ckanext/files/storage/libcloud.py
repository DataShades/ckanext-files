from __future__ import annotations

import dataclasses
from typing import Any

from file_keeper.default.adapters import libcloud as lc
from typing_extensions import override

from ckan.config.declaration import Declaration, Key

from ckanext.files import shared

PROVIDERS_URL = "https://libcloud.readthedocs.io/en/stable/storage/" + "supported_providers.html#provider-matrix"

get_driver: Any


@dataclasses.dataclass()
class Settings(shared.Settings, lc.Settings):
    pass


class LibCloudStorage(shared.Storage, lc.LibCloudStorage):  # pyright: ignore[reportIncompatibleVariableOverride]
    settings: Settings  # pyright: ignore[reportIncompatibleVariableOverride]
    SettingsFactory = Settings
    ReaderFactory = type("Reader", (shared.Reader, lc.Reader), {})
    ManagerFactory = type("Manager", (shared.Manager, lc.Manager), {})
    UploaderFactory = type("Uploader", (shared.Uploader, lc.Uploader), {})

    @override
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
            "JSON object with additional parameters" + " passed directly to storage constructor.",
        ).set_validators("default({}) convert_to_json_if_string dict_only")

        declaration.declare(key.public_prefix).set_description(
            "URL prefix to use when builing public file's URL. Usually, this "
            "requires a container with public URL. For example, if storage "
            "uses cloud provider `example.cloud.com` and files are uploaded "
            "into container `my_files`, the public prefix must be set to "
            "`https://certain.cloud.com/my_files`, assuming container can be "
            "anonymously accessed via this URL. File location will be appended"
            " to public prefix, producing absolute public URL."
        )
