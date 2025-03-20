from __future__ import annotations

import base64
import dataclasses

from file_keeper.default.adapters import s3

from ckan.config.declaration import Declaration, Key

from ckanext.files import shared


def decode(value: str) -> str:
    return base64.decodebytes(value.encode()).hex()


@dataclasses.dataclass()
class Settings(shared.Settings, s3.Settings):
    pass


class S3Storage(shared.Storage, s3.S3Storage):
    hidden = True
    settings: Settings  # type: ignore
    SettingsFactory = Settings

    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        super().declare_config_options(declaration, key)

        declaration.declare(key.bucket).required().set_description(
            "Name of the S3 bucket where uploaded data will be stored.",
        )
        declaration.declare(key.path, "").set_description(
            "Path to the folder where uploaded data will be stored.",
        )
        declaration.declare(key.key).set_description("The access key for AWS account.")
        declaration.declare(key.secret).set_description(
            "The secret key for AWS account."
        )

        declaration.declare(key.region).set_description(
            "The AWS Region used in instantiating the client."
        )

        declaration.declare(key.endpoint).set_description(
            "The complete URL to use for the constructed client."
        )
