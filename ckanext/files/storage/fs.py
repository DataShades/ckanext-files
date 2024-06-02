from __future__ import annotations

import copy
import logging
import os
from typing import IO, Any

import magic

import ckan.plugins.toolkit as tk
from ckan.config.declaration import Declaration, Key

from ckanext.files import exceptions, shared, types, utils
from ckanext.files.base import (
    FileData,
    HashingReader,
    Manager,
    MultipartData,
    Reader,
    Storage,
    Uploader,
)

log = logging.getLogger(__name__)
CHUNK_SIZE = 16384


class FileSystemUploader(Uploader):
    required_options = ["path"]
    capabilities = shared.Capability.combine(
        shared.Capability.CREATE,
        shared.Capability.MULTIPART_UPLOAD,
    )

    def upload(
        self,
        location: str,
        upload: types.Upload,
        extras: dict[str, Any],
    ) -> FileData:
        filename = self.storage.compute_location(location, extras, upload)
        filepath = os.path.join(self.storage.settings["path"], filename)

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        reader = HashingReader(upload.stream)
        with open(filepath, "wb") as dest:
            for chunk in reader:
                dest.write(chunk)

        return FileData(
            filename,
            os.path.getsize(filepath),
            upload.content_type,
            reader.get_hash(),
        )

    def initialize_multipart_upload(
        self,
        location: str,
        extras: dict[str, Any],
    ) -> MultipartData:
        schema: dict[str, Any] = {
            "size": [
                tk.get_validator("not_missing"),
                tk.get_validator("int_validator"),
            ],
            "__extras": [tk.get_validator("ignore")],
        }
        data, errors = tk.navl_validate(extras, schema)

        if errors:
            raise tk.ValidationError(errors)

        upload = types.Upload(content_length=data["size"])

        max_size = self.storage.max_size
        if max_size:
            utils.ensure_size(upload, max_size)

        tmp_result = self.upload(location, upload, data)
        result = MultipartData(
            tmp_result.location,
            data["size"],
            "application/octet-stream",
            storage_data={"uploaded": 0},
        )
        return result

    def show_multipart_upload(self, upload_data: MultipartData) -> MultipartData:
        return upload_data

    def update_multipart_upload(
        self,
        upload_data: MultipartData,
        extras: dict[str, Any],
    ) -> MultipartData:
        upload_data = copy.deepcopy(upload_data)
        schema = {
            "position": [
                tk.get_validator("ignore_missing"),
                tk.get_validator("int_validator"),
            ],
            "upload": [
                tk.get_validator("not_missing"),
                tk.get_validator("files_into_upload"),
            ],
            "__extras": [tk.get_validator("ignore")],
        }
        data, errors = tk.navl_validate(extras, schema)

        if errors:
            raise tk.ValidationError(errors)

        data.setdefault("position", upload_data.storage_data["uploaded"])
        upload: types.Upload = data["upload"]

        expected_size = data["position"] + upload.content_length
        if expected_size > upload_data.size:
            raise exceptions.UploadOutOfBoundError(expected_size, upload_data.size)

        filepath = os.path.join(
            str(self.storage.settings["path"]),
            upload_data.location,
        )
        with open(filepath, "rb+") as dest:
            dest.seek(data["position"])
            dest.write(upload.stream.read())

        upload_data.storage_data["uploaded"] = os.path.getsize(filepath)
        return upload_data

    def complete_multipart_upload(
        self,
        upload_data: MultipartData,
        extras: dict[str, Any],
    ) -> FileData:
        filepath = os.path.join(
            str(self.storage.settings["path"]),
            upload_data.location,
        )
        size = os.path.getsize(filepath)
        if size != upload_data.size:
            raise tk.ValidationError(
                {
                    "size": [
                        "Actual filesize {} does not match expected {}".format(
                            size,
                            upload_data.size,
                        ),
                    ],
                },
            )

        with open(filepath, "rb") as src:
            reader = HashingReader(src)
            content_type = magic.from_buffer(next(reader, b""), True)
            reader.exhaust()

        return FileData(upload_data.location, size, content_type, reader.get_hash())


class FileSystemManager(Manager):
    required_options = ["path"]
    capabilities = shared.Capability.combine(
        shared.Capability.REMOVE,
        shared.Capability.ANALYZE,
    )

    def remove(self, data: FileData) -> bool:
        filepath = os.path.join(str(self.storage.settings["path"]), data.location)
        if not os.path.exists(filepath):
            return False

        os.remove(filepath)
        return True

    def analyze(self, filename: str) -> FileData:
        """Return all details about filename."""
        filepath = os.path.join(str(self.storage.settings["path"]), filename)
        if not os.path.exists(filepath):
            raise exceptions.MissingFileError(self.storage.settings["name"], filepath)

        with open(filepath, "rb") as src:
            reader = HashingReader(src)
            content_type = magic.from_buffer(next(reader, b""), True)
            reader.exhaust()

        return FileData(
            filename,
            size=os.path.getsize(filepath),
            content_type=content_type,
            hash=reader.get_hash(),
        )


class FileSystemReader(Reader):
    required_options = ["path"]
    capabilities = shared.Capability.combine(shared.Capability.STREAM)

    def stream(self, data: FileData) -> IO[bytes]:
        filepath = os.path.join(str(self.storage.settings["path"]), data.location)
        if not os.path.exists(filepath):
            raise exceptions.MissingFileError(self.storage.settings["name"], filepath)

        return open(filepath, "rb")


class FileSystemStorage(Storage):
    """Store files in local filesystem."""

    def make_uploader(self):
        return FileSystemUploader(self)

    def make_reader(self):
        return FileSystemReader(self)

    def make_manager(self):
        return FileSystemManager(self)

    def __init__(self, **settings: Any) -> None:
        path = self.ensure_option(settings, "path")

        if not os.path.exists(path):
            if tk.asbool(settings.get("create_path")):
                os.makedirs(path)
            else:
                raise exceptions.InvalidStorageConfigurationError(
                    type(self),
                    "path `{}` does not exist".format(path),
                )

        super(FileSystemStorage, self).__init__(**settings)

    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        super().declare_config_options(declaration, key)
        declaration.declare(key.path).required().set_description(
            "Path to the folder where uploaded data will be stored.",
        )
        declaration.declare_bool(key.create_path).set_description(
            "Create storage folder if it does not exist.",
        )


class PublicFileSystemStorage(FileSystemStorage):
    def __init__(self, **settings: Any) -> None:
        self.ensure_option(settings, "public_root")
        super(PublicFileSystemStorage, self).__init__(**settings)

    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key) -> None:
        super().declare_config_options(declaration, key)
        declaration.declare(key.public_root).required().set_description(
            "URL of the storage folder."
            + " `public_root + filename` must produce a public URL",
        )
