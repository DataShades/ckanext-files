from __future__ import annotations

import copy
import glob
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
    Manager,
    MultipartData,
    Reader,
    Storage,
    Uploader,
)

log = logging.getLogger(__name__)
CHUNK_SIZE = 16384


class FsStorage(Storage):
    """Store files in local filesystem."""

    def make_uploader(self):
        return FsUploader(self)

    def make_reader(self):
        return FsReader(self)

    def make_manager(self):
        return FsManager(self)

    @classmethod
    def prepare_settings(cls, settings: dict[str, Any]):
        settings.setdefault("create_path", False)
        settings.setdefault("recursive", False)

        return super().prepare_settings(settings)

    def __init__(self, settings: Any):
        path = self.ensure_option(settings, "path")

        if not os.path.exists(path):
            if tk.asbool(self.ensure_option(settings, "create_path")):
                os.makedirs(path)
            else:
                raise exceptions.InvalidStorageConfigurationError(
                    type(self),
                    f"path `{path}` does not exist",
                )

        super().__init__(settings)

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


class FsUploader(Uploader):
    required_options = ["path"]
    capabilities = shared.Capability.CREATE | shared.Capability.MULTIPART

    def upload(
        self,
        location: str,
        upload: shared.Upload,
        extras: dict[str, Any],
    ) -> FileData:
        location = self.storage.compute_location(location, upload, **extras)
        dest = os.path.join(self.storage.settings["path"], location)

        if os.path.exists(dest) and not self.storage.settings["override_existing"]:
            raise exceptions.ExistingFileError(self.storage, dest)

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

        # validation happens here
        tmp_result = self.storage.upload(location, upload, **extras)

        data.location = tmp_result.location
        data.storage_data = dict(tmp_result.storage_data, uploaded=0)
        return data

    def multipart_refresh(
        self,
        data: MultipartData,
        extras: dict[str, Any],
    ) -> MultipartData:
        filepath = os.path.join(
            str(self.storage.settings["path"]),
            data.location,
        )
        data.storage_data["uploaded"] = os.path.getsize(filepath)

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
    capabilities = (
        shared.Capability.REMOVE
        | shared.Capability.SCAN
        | shared.Capability.EXISTS
        | shared.Capability.ANALYZE
        | shared.Capability.COPY
        | shared.Capability.MOVE
        | shared.Capability.COMPOSE
        | shared.Capability.APPEND
    )

    def compose(
        self,
        datas: Iterable[FileData],
        location: str,
        extras: dict[str, Any],
    ) -> FileData:
        """Combine multipe file inside the storage into a new one."""
        location = self.storage.compute_location(location, **extras)
        dest = os.path.join(self.storage.settings["path"], location)
        if os.path.exists(dest) and not self.storage.settings["override_existing"]:
            raise exceptions.ExistingFileError(self.storage, dest)

        sources: list[str] = []
        for data in datas:
            src = os.path.join(str(self.storage.settings["path"]), data.location)

            if not os.path.exists(src):
                raise exceptions.MissingFileError(self.storage, src)
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
            raise exceptions.MissingFileError(self.storage, src)

        if os.path.exists(dest) and not self.storage.settings["override_existing"]:
            raise exceptions.ExistingFileError(self.storage, dest)

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
            raise exceptions.MissingFileError(self.storage, src)

        if os.path.exists(dest):
            if self.storage.settings["override_existing"]:
                os.remove(dest)
            else:
                raise exceptions.ExistingFileError(self.storage, dest)

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
        search_path = os.path.join(path, "**")

        for entry in glob.glob(
            search_path,
            recursive=self.storage.settings["recursive"],
        ):
            if not os.path.isfile(entry):
                continue
            yield os.path.relpath(entry, path)

    def analyze(self, location: str, extras: dict[str, Any]) -> FileData:
        """Return all details about location."""
        filepath = os.path.join(str(self.storage.settings["path"]), location)
        if not os.path.exists(filepath):
            raise exceptions.MissingFileError(self.storage, filepath)

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

    capabilities = shared.Capability.STREAM | shared.Capability.TEMPORAL_LINK

    def stream(self, data: FileData, extras: dict[str, Any]) -> IO[bytes]:
        filepath = os.path.join(str(self.storage.settings["path"]), data.location)
        if not os.path.exists(filepath):
            raise exceptions.MissingFileError(self.storage, filepath)

        return open(filepath, "rb")  # noqa: SIM115


class PublicFsReader(FsReader):
    required_options = FsReader.required_options + ["public_root"]

    capabilities = FsReader.capabilities | utils.Capability.PUBLIC_LINK

    def public_link(self, data: FileData, extras: dict[str, Any]) -> str:
        """Return public download link."""
        return "/".join(
            [
                self.storage.settings["public_root"].rstrip("/"),
                data.location.lstrip("/"),
            ],
        )


class PublicFsStorage(FsStorage):
    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        super().declare_config_options(declaration, key)

        declaration.declare(key.public_root).required().set_description(
            "URL of the storage folder."
            + " `public_root + location` must produce a public URL",
        )

    def make_reader(self):
        return PublicFsReader(self)


class CkanResourceFsStorage(FsStorage):
    def __init__(self, settings: Any):
        settings["recursive"] = True
        super().__init__(settings)
