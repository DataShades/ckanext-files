from __future__ import annotations

import base64
import dataclasses
import re

from file_keeper.default.adapters import gcs

import ckan.plugins.toolkit as tk
from ckan.config.declaration import Declaration, Key

from ckanext.files import shared

RE_RANGE = re.compile(r"bytes=(?P<first_byte>\d+)-(?P<last_byte>\d+)")
HTTP_RESUME = 308


def decode(value: str) -> str:
    return base64.decodebytes(value.encode()).hex()


@dataclasses.dataclass()
class Settings(shared.Settings, gcs.Settings):
    pass


class GoogleCloudStorage(shared.Storage, gcs.GoogleCloudStorage):
    hidden = True

    settings: Settings  # type: ignore
    SettingsFactory = Settings

    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        super().declare_config_options(declaration, key)
        declaration.declare(key.path, "").set_description(
            "Path to the folder where uploaded data will be stored.",
        )
        declaration.declare(key.bucket).required().set_description(
            "Name of the GCS bucket where uploaded data will be stored.",
        )
        declaration.declare(key.credentials_file).set_description(
            "Path to the credentials file used for authentication by GCS client."
            + "\nIf empty, uses value of GOOGLE_APPLICATION_CREDENTIALS envvar.",
        )
        declaration.declare(
            key.resumable_origin,
            tk.config["ckan.site_url"],
        ).set_description(
            "Value of the Origin header set for resumable upload."
            + "\nIn most cases, keep it the same as CKAN base URL.",
        )
