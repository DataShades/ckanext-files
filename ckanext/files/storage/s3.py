from __future__ import annotations

import dataclasses

from file_keeper.default.adapters import s3
from typing_extensions import override

from ckan.config.declaration import Declaration, Key

from ckanext.files import shared


@dataclasses.dataclass()
class Settings(shared.Settings, s3.Settings):
    pass


class S3Storage(shared.Storage, s3.S3Storage):  # pyright: ignore[reportIncompatibleVariableOverride]
    """AWS S3 adapter."""

    settings: Settings  # pyright: ignore[reportIncompatibleVariableOverride]
    SettingsFactory = Settings
    ReaderFactory = type("Reader", (shared.Reader, s3.Reader), {})
    UploaderFactory = type("Reader", (shared.Uploader, s3.Uploader), {})
    ManagerFactory = type("Reader", (shared.Manager, s3.Manager), {})

    @override
    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        super().declare_config_options(declaration, key)

        declaration.declare(key.bucket).required().set_description(
            "Name of the S3 bucket where uploaded data will be stored.",
        )
        declaration.declare(key.key).set_description("The access key for AWS account.")
        declaration.declare(key.secret).set_description("The secret key for AWS account.")
        declaration.declare(key.endpoint).set_description("Custom AWS endpoint.")

        declaration.declare(key.region).set_description("The AWS Region used in instantiating the client.")
