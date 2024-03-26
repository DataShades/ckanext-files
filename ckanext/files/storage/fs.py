import logging
import os

import magic
from werkzeug.datastructures import FileStorage

import ckan.plugins.toolkit as tk

from ckanext.files import exceptions, types, utils
from ckanext.files.base import (
    Capability,
    HashingReader,
    Manager,
    Reader,
    Storage,
    Uploader,
)

FsAdditionalData = types.TypedDict("FsAdditionalData", {})


class FsStorageData(FsAdditionalData, types.MinimalStorageData):
    pass


log = logging.getLogger(__name__)
CHUNK_SIZE = 16384


class FileSystemUploader(Uploader):
    required_options = ["path"]
    capabilities = utils.combine_capabilities(
        Capability.CREATE,
        Capability.MULTIPART_UPLOAD,
    )

    def upload(self, name, upload, extras):
        # type: (str, types.Upload, dict[str, types.Any]) -> FsStorageData
        filename = self.compute_name(name, extras, upload)
        filepath = os.path.join(self.storage.settings["path"], filename)

        reader = HashingReader(upload.stream)
        with open(filepath, "wb") as dest:
            for chunk in reader:
                dest.write(chunk)

        return {
            "filename": filename,
            "content_type": upload.content_type,
            "size": os.path.getsize(filepath),
            "hash": reader.get_hash(),
        }

    def initialize_multipart_upload(self, name, extras):
        # type: (str, dict[str, types.Any]) -> dict[str, types.Any]
        schema = {
            "size": [
                tk.get_validator("not_missing"),
                tk.get_validator("int_validator"),
            ],
            "__extras": [tk.get_validator("ignore")],
        }  # type: dict[str, types.Any]
        data, errors = tk.navl_validate(extras, schema)

        if errors:
            raise tk.ValidationError(errors)

        upload = FileStorage(content_length=data["size"])

        max_size = self.storage.max_size
        if max_size:
            utils.ensure_size(upload, max_size)

        result = dict(self.upload(name, upload, data))
        result["size"] = data["size"]
        result["content_type"] = "application/octet-stream"
        result["uploaded"] = 0

        return result

    def show_multipart_upload(self, upload_data):
        # type: (dict[str, types.Any]) -> dict[str, types.Any]
        return upload_data

    def update_multipart_upload(self, upload_data, extras):
        # type: (dict[str, types.Any], dict[str, types.Any]) -> dict[str, types.Any]
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

        data.setdefault("position", upload_data["uploaded"])
        upload = data["upload"]  # type: types.Upload

        expected_size = data["position"] + upload.content_length
        if expected_size > upload_data["size"]:
            raise exceptions.UploadOutOfBoundError(expected_size, upload_data["size"])

        filepath = os.path.join(
            str(self.storage.settings["path"]),
            upload_data["filename"],
        )
        with open(filepath, "rb+") as dest:
            dest.seek(data["position"])
            dest.write(upload.stream.read())

        upload_data["uploaded"] = os.path.getsize(filepath)
        return upload_data

    def complete_multipart_upload(self, upload_data, extras):
        # type: (dict[str, types.Any], dict[str, types.Any]) -> FsStorageData
        filepath = os.path.join(
            str(self.storage.settings["path"]),
            upload_data["filename"],
        )
        size = os.path.getsize(filepath)
        if size != upload_data["size"]:
            raise tk.ValidationError(
                {
                    "size": [
                        "Actual filesize {} does not match expected {}".format(
                            size,
                            upload_data["size"],
                        ),
                    ],
                },
            )

        with open(filepath, "rb") as src:
            reader = HashingReader(src)
            it = iter(reader)
            content_type = magic.from_buffer(next(it, b""), True)

            # exhaust reader to get the checksum
            for _chunk in it:
                pass

        return {
            "filename": upload_data["filename"],
            "content_type": content_type,
            "size": size,
            "hash": reader.get_hash(),
        }


class FileSystemManager(Manager):
    required_options = ["path"]
    capabilities = utils.combine_capabilities(Capability.REMOVE)

    def remove(self, data):
        # type: (dict[str, types.Any]) -> bool
        filepath = os.path.join(str(self.storage.settings["path"]), data["filename"])
        if not os.path.exists(filepath):
            return False

        os.remove(filepath)
        return True


class FileSystemReader(Reader):
    required_options = ["path"]
    capabilities = utils.combine_capabilities(Capability.STREAM)

    def stream(self, data):
        # type: (dict[str, types.Any]) -> types.IO[bytes]
        filepath = os.path.join(str(self.storage.settings["path"]), data["filename"])
        if not os.path.exists(filepath):
            raise exceptions.MissingFileError(self.storage.settings["name"], filepath)

        return open(filepath, "rb")


class FileSystemStorage(Storage):
    def make_uploader(self):
        return FileSystemUploader(self)

    def make_reader(self):
        return FileSystemReader(self)

    def make_manager(self):
        return FileSystemManager(self)

    def __init__(self, **settings):
        # type: (**types.Any) -> None
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
    def declare_config_options(cls, declaration, key):  # pragma: no cover
        # type: (types.Declaration, types.Key) -> None
        super().declare_config_options(declaration, key)
        declaration.declare(key.path).required().set_description(
            "Path to the folder where uploaded data will be stored.",
        )
        declaration.declare_bool(key.create_path).set_description(
            "Create storage folder if it does not exist.",
        )


class PublicFileSystemStorage(FileSystemStorage):
    def __init__(self, **settings):
        # type: (**types.Any) -> None
        self.ensure_option(settings, "public_root")
        super(PublicFileSystemStorage, self).__init__(**settings)

    @classmethod
    def declare_config_options(cls, declaration, key):  # pragma: no cover
        # type: (types.Declaration, types.Key) -> None
        super().declare_config_options(declaration, key)
        declaration.declare(key.public_root).required().set_description(
            "URL of the storage folder."
            + " `public_root + filename` must produce a public URL",
        )
