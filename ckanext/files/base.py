"""Base abstract functionality of the extentsion.

All classes required for specific storage implementations are defined
here. Some utilities, like `make_storage` are also added to this module instead
of `utils` to avoid import cycles.

This module relies only on types, exceptions and utils to prevent import
cycles.

"""

from __future__ import annotations

from time import time
from typing import Any

import file_keeper as fk

import ckan.plugins.toolkit as tk
from ckan.config.declaration import Declaration, Key

from . import config, exceptions, model, utils

adapters = fk.adapters
storages = fk.Registry["Storage"]({})
Settings = fk.Settings

FileData: type[fk.FileData[model.File]] = fk.FileData
MultipartData: type[fk.MultipartData[model.Multipart]] = fk.MultipartData

make_storage = fk.make_storage


def get_storage(name: str | None = None) -> Storage:
    """Return existing storage instance.

    Storages are initialized when plugin is loaded. As result, this function
    always returns the same storage object for the given name.

    If no name specified, default storage is returned.

    Args:
        name: name of the configured storage

    Returns:
        storage instance

    Raises:
        exceptions.UnknownStorageError: storage with the given name is not
            configured

    Example:
        ```
        default_storage = get_storage()
        storage = get_storage("storage name")
        ```

    """
    if name is None:
        name = config.default_storage()

    storage = storages.get(name)

    if not storage:
        raise exceptions.UnknownStorageError(name)

    return storage


class Uploader(fk.Uploader):
    """Service responsible for writing data into a storage.

    `Storage` internally calls methods of this service. For example,
    `Storage.upload(location, upload, **kwargs)` results in
    `Uploader.upload(location, upload, kwargs)`.

    Example:
        ```python
        class MyUploader(Uploader):
            def upload(
                self, location: str, upload: Upload, extras: dict[str, Any]
            ) -> FileData:
                reader = upload.hashing_reader()

                with open(location, "wb") as dest:
                    dest.write(reader.read())

                return FileData(
                    location, upload.size,
                    upload.content_type,
                    reader.get_hash()
                )
        ```
    """


class Manager(fk.Manager):
    """Service responsible for maintenance file operations.

    `Storage` internally calls methods of this service. For example,
    `Storage.remove(data, **kwargs)` results in `Manager.remove(data, kwargs)`.

    Example:
        ```python
        class MyManager(Manager):
            def remove(
                self, data: FileData|MultipartData, extras: dict[str, Any]
            ) -> bool:
                os.remove(data.location)
                return True
        ```
    """


class Reader(fk.Reader):
    """Service responsible for reading data from the storage.

    `Storage` internally calls methods of this service. For example,
    `Storage.stream(data, **kwargs)` results in `Reader.stream(data, kwargs)`.

    Example:
        ```python
        class MyReader(Reader):
            def stream(
                self, data: FileData, extras: dict[str, Any]
            ) -> Iterable[bytes]:
                return open(data.location, "rb")
        ```
    """

    def temporal_link(self, data: FileData, extras: dict[str, Any]) -> str:
        """Return temporal download link.

        extras["ttl"] controls lifetime of the link(30 seconds by default).

        """
        token = utils.encode_token(
            {
                "topic": "download_file",
                "exp": str(int(time()) + extras.get("ttl", 30)),
                "storage": self.storage.settings["name"],
                "location": data.location,
            },
        )
        return tk.url_for("files.temporal_download", token=token, _external=True)


class Storage(fk.Storage):
    """Base class for storage implementation.

    Args:
        settings: storage configuration

    Example:
        ```python
        class MyStorage(Storage):
            def make_uploader(self):
                return MyUploader(self)

            def make_reader(self):
                return MyReader(self)

            def make_manager(self):
                return MyManager(self)
        ```
    """

    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        declaration.declare(key.max_size, 0).append_validators(
            "files_parse_filesize",
        ).set_description(
            "The maximum size of a single upload."
            + "\nSupports size suffixes: 42B, 2M, 24KiB, 1GB."
            + " `0` means no restrictions.",
        )

        declaration.declare_list(key.supported_types, None).set_description(
            "Space-separated list of MIME types or just type or subtype part."
            + "\nExample: text/csv pdf application video jpeg",
        )

        declaration.declare_bool(key.override_existing).set_description(
            "If file already exists, replace it with new content.",
        )

        declaration.declare(key.name, key[-1]).set_description(
            "Descriptive name of the storage used for debugging. When empty,"
            + " name from the config option is used,"
            + " i.e: `ckanext.files.storage.DEFAULT_NAME...`",
        )
