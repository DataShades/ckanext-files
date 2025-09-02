from __future__ import annotations

import dataclasses
import logging
import os
from typing import Any

import file_keeper as fk
import flask
from file_keeper.default.adapters import fs
from typing_extensions import override

from ckan import types
from ckan.config.declaration import Declaration, Key

from ckanext.files import shared

log = logging.getLogger(__name__)
CHUNK_SIZE = 16384


@dataclasses.dataclass()
class Settings(shared.Settings, fs.Settings):
    pass


class Reader(shared.Reader, fs.Reader):
    @override
    def response(self, data: shared.FileData, extras: dict[str, Any]) -> types.Response:
        filepath = os.path.join(self.storage.settings.path, data.location)
        return flask.send_file(
            filepath,
            download_name=data.location,
            mimetype=data.content_type,
        )


class FsStorage(shared.Storage, fs.FsStorage):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Store files in local filesystem."""

    settings: Settings  # pyright: ignore[reportIncompatibleVariableOverride]
    SettingsFactory: type[shared.Settings] = Settings  # pyright: ignore[reportIncompatibleVariableOverride]
    ReaderFactory: type[shared.Reader] = Reader  # pyright: ignore[reportIncompatibleVariableOverride]
    UploaderFactory = type("Uploader", (shared.Uploader, fs.Uploader), {})
    ManagerFactory = type("Manager", (shared.Manager, fs.Manager), {})


class PublicFsReader(Reader):
    capabilities = fs.Reader.capabilities | fk.Capability.LINK_PERMANENT
    storage: PublicFsStorage  # pyright: ignore[reportIncompatibleVariableOverride]

    @override
    def permanent_link(self, data: fk.FileData, extras: dict[str, Any]) -> str:
        """Return public download link."""
        from ckan.lib.helpers import url_for_static  # noqa: PLC0415

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
    settings: PublicFsSettings  # pyright: ignore[reportIncompatibleVariableOverride]
    SettingsFactory = PublicFsSettings
    ReaderFactory = PublicFsReader

    @override
    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        super().declare_config_options(declaration, key)

        declaration.declare(key.public_prefix).set_description(
            "URL of the storage folder." + " `public_prefix + location` must produce a public URL",
        )


class CkanResourceFsStorage(FsStorage):
    pass
