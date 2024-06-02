from __future__ import annotations

import copy
import logging
import os
import shutil
from io import BytesIO
from typing import IO, Any, Iterable

import magic

import ckan.plugins.toolkit as tk
from ckan.config.declaration import Declaration, Key

from ckanext.files import exceptions, shared, utils
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
        upload: utils.Upload,
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
            upload.type,
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

        upload = utils.Upload(
            BytesIO(),
            location,
            data["size"],
            "application/octet-stream",
        )

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
        upload: utils.Upload = data["upload"]

        expected_size = data["position"] + upload.size
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
        shared.Capability.SCAN,
        shared.Capability.EXISTS,
        shared.Capability.ANALYZE,
        shared.Capability.COPY,
        shared.Capability.MOVE,
        shared.Capability.COMPOSE,
        shared.Capability.APPEND,
    )

    def compose(
        self,
        datas: Iterable[FileData],
        location: str,
        extras: dict[str, Any],
    ) -> FileData:
        """Combine multipe file inside the storage into a new one."""

        safe_location = self.storage.compute_location(location, extras)
        dest = os.path.join(str(self.storage.settings["path"]), safe_location)
        if os.path.exists(dest):
            raise exceptions.ExistingFileError(self.storage.settings["name"], dest)

        sources: list[str] = []
        for data in datas:
            src = os.path.join(str(self.storage.settings["path"]), data.location)

            if not os.path.exists(src):
                raise exceptions.MissingFileError(self.storage.settings["name"], src)
            sources.append(src)

        with open(dest, "wb") as to_fd:
            for src in sources:
                with open(src, "rb") as from_fd:
                    shutil.copyfileobj(from_fd, to_fd)

        return self.analyze(dest)

    def append(
        self,
        data: FileData,
        upload: utils.Upload,
        extras: dict[str, Any],
    ) -> FileData:
        """Append content to existing file."""
        dest = os.path.join(str(self.storage.settings["path"]), data.location)
        with open(dest, "ab") as fd:
            fd.write(upload.stream.read())

        return self.analyze(dest)

    def copy(
        self,
        data: FileData,
        location: str,
        extras: dict[str, Any],
    ) -> FileData:
        """Copy file inside the storage."""
        safe_location = self.storage.compute_location(location, extras)
        src = os.path.join(str(self.storage.settings["path"]), data.location)
        dest = os.path.join(str(self.storage.settings["path"]), safe_location)

        if not os.path.exists(src):
            raise exceptions.MissingFileError(self.storage.settings["name"], src)

        if os.path.exists(dest):
            raise exceptions.ExistingFileError(self.storage.settings["name"], dest)

        shutil.copy(src, dest)
        new_data = copy.deepcopy(data)
        new_data.location = safe_location
        return new_data

    def move(
        self,
        data: FileData,
        location: str,
        extras: dict[str, Any],
    ) -> FileData:
        """Move file to a different location inside the storage."""
        safe_location = self.storage.compute_location(location, extras)
        src = os.path.join(str(self.storage.settings["path"]), data.location)
        dest = os.path.join(str(self.storage.settings["path"]), safe_location)

        if not os.path.exists(src):
            raise exceptions.MissingFileError(self.storage.settings["name"], src)

        if os.path.exists(dest):
            raise exceptions.ExistingFileError(self.storage.settings["name"], dest)

        shutil.move(src, dest)
        new_data = copy.deepcopy(data)
        new_data.location = safe_location
        return new_data

    def exists(self, data: FileData) -> bool:
        filepath = os.path.join(str(self.storage.settings["path"]), data.location)
        return os.path.exists(filepath)

    def remove(self, data: FileData) -> bool:
        filepath = os.path.join(str(self.storage.settings["path"]), data.location)
        if not os.path.exists(filepath):
            return False

        os.remove(filepath)
        return True

    def scan(self) -> Iterable[str]:
        path = self.storage.settings["path"]
        for entry in os.scandir(path):
            if not entry.is_file():
                continue
            yield entry.name

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
