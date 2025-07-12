from __future__ import annotations

import dataclasses
import logging
import os
from typing import Any

import file_keeper as fk
import flask
from file_keeper.default.adapters import fs

from ckan import types
from ckan.config.declaration import Declaration, Key

from ckanext.files import shared

log = logging.getLogger(__name__)
CHUNK_SIZE = 16384


@dataclasses.dataclass()
class Settings(shared.Settings, fs.Settings):
    pass


class FsStorage(shared.Storage, fs.FsStorage):
    """Store files in local filesystem."""

    settings: Settings  # type: ignore
    SettingsFactory = Settings

    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        super().declare_config_options(declaration, key)
        declaration.declare(key.path).required().set_description(
            "Path to the folder where uploaded data will be stored.",
        )

        declaration.declare_bool(key.create_path).set_description(
            "Create storage folder if it does not exist.",
        )

        declaration.declare_bool(key.recursive).set_description(
            "Use this flag if files can be stored inside subfolders"
            + " of the main storage path.",
        )

    def _base_response(
        self, data: fk.FileData, extras: dict[str, Any]
    ) -> types.Response:
        filepath = os.path.join(self.settings.path, data.location)
        return flask.send_file(
            filepath,
            download_name=data.location,
            mimetype=data.content_type,
        )


class PublicFsReader(fs.Reader):
    capabilities = fs.Reader.capabilities | fk.Capability.PERMANENT_LINK
    storage: PublicFsStorage  # type: ignore

    def permanent_link(self, data: fk.FileData, extras: dict[str, Any]) -> str:
        """Return public download link."""
        from ckan.lib.helpers import url_for_static

        return url_for_static(
            os.path.join(
                self.storage.settings.public_prefix,
                data.location,
            ),
            _external=True,
        )


@dataclasses.dataclass()
class PublicFsSettings(Settings):
    public_prefix: str = "/"


class PublicFsStorage(FsStorage):
    settings: PublicFsSettings  # type: ignore
    SettingsFactory = PublicFsSettings
    ReaderFactory = PublicFsReader

    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        super().declare_config_options(declaration, key)

        declaration.declare(key.public_prefix).set_description(
            "URL of the storage folder."
            + " `public_prefix + location` must produce a public URL",
        )


class CkanResourceFsStorage(FsStorage):
    def __init__(self, settings: Any):
        settings["recursive"] = True
        super().__init__(settings)
