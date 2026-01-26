from __future__ import annotations

import dataclasses

from file_keeper.default.adapters import azure_blob
from typing_extensions import override

from ckan.config.declaration import Declaration, Key

from ckanext.files import shared


@dataclasses.dataclass()
class Settings(shared.Settings, azure_blob.Settings):
    pass


class AzureBlobStorage(shared.Storage, azure_blob.AzureBlobStorage):  # pyright: ignore[reportIncompatibleVariableOverride]
    """AWS S3 adapter."""

    settings: Settings  # pyright: ignore[reportIncompatibleVariableOverride]
    SettingsFactory = Settings
    ReaderFactory = type("Reader", (shared.Reader, azure_blob.Reader), {})
    UploaderFactory = type("Reader", (shared.Uploader, azure_blob.Uploader), {})
    ManagerFactory = type("Reader", (shared.Manager, azure_blob.Manager), {})

    @override
    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        super().declare_config_options(declaration, key)

        declaration.declare(key.account_name).set_description("Name of the account.")
        declaration.declare(key.account_key).required().set_description("Key for the account.")
        declaration.declare(key.account_url, "https://{account_name}.blob.core.windows.net").set_description(
            "Custom resource URL."
        )
        declaration.declare(key.container_name).required().set_description("Name of the storage container.")
