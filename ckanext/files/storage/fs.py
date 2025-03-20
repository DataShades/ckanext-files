from __future__ import annotations

import dataclasses
import logging
from typing import Any

import file_keeper as fk
from file_keeper.default.adapters import fs

from ckan.config.declaration import Declaration, Key

from ckanext.files.base import Storage

log = logging.getLogger(__name__)
CHUNK_SIZE = 16384


class FsStorage(Storage, fs.FsStorage):
    """Store files in local filesystem."""

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


class PublicFsReader(fs.Reader):
    capabilities = fs.Reader.capabilities | fk.Capability.PERMANENT_LINK
    storage: PublicFsStorage  # type: ignore

    def permanent_link(self, data: fk.FileData, extras: dict[str, Any]) -> str:
        """Return public download link."""
        return "/".join(
            [
                self.storage.settings.public_root.rstrip("/"),
                data.location.lstrip("/"),
            ],
        )


@dataclasses.dataclass()
class PublicFsSettings(fs.Settings):
    public_root: str = "/"


class PublicFsStorage(FsStorage):
    settings: PublicFsSettings  # type: ignore
    SettingsFactory = PublicFsSettings
    ReaderFactory = PublicFsReader

    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        super().declare_config_options(declaration, key)

        declaration.declare(key.public_root).set_description(
            "URL of the storage folder."
            + " `public_root + location` must produce a public URL",
        )


class CkanResourceFsStorage(FsStorage):
    def __init__(self, settings: Any):
        settings["recursive"] = True
        super().__init__(settings)
