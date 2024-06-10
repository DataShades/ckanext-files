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

from ckanext.files import exceptions, shared
from ckanext.files.base import (
    FileData,
    Manager,
    MultipartData,
    Reader,
    Storage,
    Uploader,
)

log = logging.getLogger(__name__)
CHUNK_SIZE = 16384


class FsUploader(Uploader):
    required_options = ["path"]
    capabilities = shared.Capability.combine(
        shared.Capability.CREATE,
        shared.Capability.MULTIPART,
    )

    def upload(
        self,
        location: str,
        upload: shared.Upload,
        extras: dict[str, Any],
    ) -> FileData:
        location = self.storage.compute_location(location, upload, **extras)
        dest = os.path.join(self.storage.settings["path"], location)

        if os.path.exists(dest):
            raise exceptions.ExistingFileError(self.storage.settings["name"], dest)

        os.makedirs(os.path.dirname(dest), exist_ok=True)
        reader = shared.HashingReader(upload.stream)
        with open(dest, "wb") as fd:
            for chunk in reader:
                fd.write(chunk)

        return FileData(
            location,
            os.path.getsize(dest),
            upload.content_type,
            reader.get_hash(),
        )

    def multipart_start(
        self,
        location: str,
        data: MultipartData,
        extras: dict[str, Any],
    ) -> MultipartData:
        upload = shared.Upload(
            BytesIO(),
            location,
            data.size,
            data.content_type,
        )

        tmp_result = self.storage.upload(location, upload, **extras)
        data.location = tmp_result.location
        data.storage_data = dict(tmp_result.storage_data, uploaded=0)
        return data

    def multipart_refresh(
        self,
        data: MultipartData,
        extras: dict[str, Any],
    ) -> MultipartData:
        return data

    def multipart_update(
        self,
        data: MultipartData,
        extras: dict[str, Any],
    ) -> MultipartData:
        data = copy.deepcopy(data)
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
        valid_extras, errors = tk.navl_validate(extras, schema)

        if errors:
            raise tk.ValidationError(errors)

        valid_extras.setdefault("position", data.storage_data["uploaded"])
        upload: shared.Upload = valid_extras["upload"]

        expected_size = valid_extras["position"] + upload.size
        if expected_size > data.size:
            raise exceptions.UploadOutOfBoundError(expected_size, data.size)

        filepath = os.path.join(
            str(self.storage.settings["path"]),
            data.location,
        )
        with open(filepath, "rb+") as dest:
            dest.seek(valid_extras["position"])
            dest.write(upload.stream.read())

        data.storage_data["uploaded"] = os.path.getsize(filepath)
        return data

    def multipart_complete(
        self,
        data: MultipartData,
        extras: dict[str, Any],
    ) -> FileData:
        filepath = os.path.join(
            str(self.storage.settings["path"]),
            data.location,
        )
        size = os.path.getsize(filepath)
        if size != data.size:
            raise exceptions.UploadSizeMismatchError(size, data.size)

        with open(filepath, "rb") as src:
            reader = shared.HashingReader(src)
            content_type = magic.from_buffer(next(reader, b""), True)
            if data.content_type and content_type != data.content_type:
                raise exceptions.UploadTypeMismatchError(
                    content_type,
                    data.content_type,
                )
            reader.exhaust()

        if data.hash and data.hash != reader.get_hash():
            raise exceptions.UploadHashMismatchError(reader.get_hash(), data.hash)

        return FileData(data.location, size, content_type, reader.get_hash())


class FsManager(Manager):
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

        location = self.storage.compute_location(location, **extras)
        dest = os.path.join(str(self.storage.settings["path"]), location)
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

        return self.analyze(dest, extras)

    def append(
        self,
        data: FileData,
        upload: shared.Upload,
        extras: dict[str, Any],
    ) -> FileData:
        """Append content to existing file."""
        dest = os.path.join(str(self.storage.settings["path"]), data.location)
        with open(dest, "ab") as fd:
            fd.write(upload.stream.read())

        return self.analyze(dest, extras)

    def copy(
        self,
        data: FileData,
        location: str,
        extras: dict[str, Any],
    ) -> FileData:
        """Copy file inside the storage."""
        location = self.storage.compute_location(location, **extras)
        src = os.path.join(str(self.storage.settings["path"]), data.location)
        dest = os.path.join(str(self.storage.settings["path"]), location)

        if not os.path.exists(src):
            raise exceptions.MissingFileError(self.storage.settings["name"], src)

        if os.path.exists(dest):
            raise exceptions.ExistingFileError(self.storage.settings["name"], dest)

        shutil.copy(src, dest)
        new_data = copy.deepcopy(data)
        new_data.location = location
        return new_data

    def move(
        self,
        data: FileData,
        location: str,
        extras: dict[str, Any],
    ) -> FileData:
        """Move file to a different location inside the storage."""
        location = self.storage.compute_location(location, **extras)
        src = os.path.join(str(self.storage.settings["path"]), data.location)
        dest = os.path.join(str(self.storage.settings["path"]), location)

        if not os.path.exists(src):
            raise exceptions.MissingFileError(self.storage.settings["name"], src)

        if os.path.exists(dest):
            raise exceptions.ExistingFileError(self.storage.settings["name"], dest)

        shutil.move(src, dest)
        new_data = copy.deepcopy(data)
        new_data.location = location
        return new_data

    def exists(self, data: FileData, extras: dict[str, Any]) -> bool:
        filepath = os.path.join(str(self.storage.settings["path"]), data.location)
        return os.path.exists(filepath)

    def remove(self, data: FileData | MultipartData, extras: dict[str, Any]) -> bool:
        filepath = os.path.join(str(self.storage.settings["path"]), data.location)
        if not os.path.exists(filepath):
            return False

        os.remove(filepath)
        return True

    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        path = self.storage.settings["path"]
        for entry in os.scandir(path):
            if not entry.is_file():
                continue
            yield entry.name

    def analyze(self, location: str, extras: dict[str, Any]) -> FileData:
        """Return all details about filename."""
        filepath = os.path.join(str(self.storage.settings["path"]), location)
        if not os.path.exists(filepath):
            raise exceptions.MissingFileError(self.storage.settings["name"], filepath)

        with open(filepath, "rb") as src:
            reader = shared.HashingReader(src)
            content_type = magic.from_buffer(next(reader, b""), True)
            reader.exhaust()

        return FileData(
            location,
            size=os.path.getsize(filepath),
            content_type=content_type,
            hash=reader.get_hash(),
        )


class FsReader(Reader):
    required_options = ["path"]
    capabilities = shared.Capability.combine(shared.Capability.STREAM)

    def stream(self, data: FileData, extras: dict[str, Any]) -> IO[bytes]:
        filepath = os.path.join(str(self.storage.settings["path"]), data.location)
        if not os.path.exists(filepath):
            raise exceptions.MissingFileError(self.storage.settings["name"], filepath)

        return open(filepath, "rb")  # noqa: SIM115


class FsStorage(Storage):
    """Store files in local filesystem."""

    def make_uploader(self):
        return FsUploader(self)

    def make_reader(self):
        return FsReader(self)

    def make_manager(self):
        return FsManager(self)

    def __init__(self, **settings: Any) -> None:
        path = self.ensure_option(settings, "path")

        if not os.path.exists(path):
            if tk.asbool(settings.get("create_path")):
                os.makedirs(path)
            else:
                raise exceptions.InvalidStorageConfigurationError(
                    type(self),
                    f"path `{path}` does not exist",
                )

        super().__init__(**settings)

    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        super().declare_config_options(declaration, key)
        declaration.declare(key.path).required().set_description(
            "Path to the folder where uploaded data will be stored.",
        )
        declaration.declare_bool(key.create_path).set_description(
            "Create storage folder if it does not exist.",
        )


class PublicFileSystemStorage(FsStorage):
    def __init__(self, **settings: Any) -> None:
        self.ensure_option(settings, "public_root")
        super().__init__(**settings)

    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key) -> None:
        super().declare_config_options(declaration, key)
        declaration.declare(key.public_root).required().set_description(
            "URL of the storage folder."
            + " `public_root + filename` must produce a public URL",
        )
