import logging
import os

import magic
import six
from werkzeug.datastructures import FileStorage

import ckan.plugins.toolkit as tk

from ckanext.files import exceptions, utils

from .base import Capability, HashingReader, Manager, Storage, Uploader

if six.PY3:
    from typing import Any  # isort: skip # noqa: F401
    from typing_extensions import TypedDict

    from .base import MinimalStorageData

    FsAdditionalData = TypedDict("FsAdditionalData", {"filename": str})

    class FsStorageData(FsAdditionalData, MinimalStorageData):
        pass


log = logging.getLogger(__name__)
CHUNK_SIZE = 16384


class FileSystemUploader(Uploader):
    required_options = ["path"]
    capabilities = utils.combine_capabilities(
        Capability.CREATE,
        Capability.MULTIPART_UPLOAD,
    )

    def upload(self, name, upload, extras):  # pragma: no cover
        # type: (str, FileStorage, dict[str, Any]) -> FsStorageData
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
        # type: (str, dict[str, Any]) -> dict[str, Any]
        schema = {
            "size": [
                tk.get_validator("not_missing"),
                tk.get_validator("int_validator"),
            ],
            "__extras": [tk.get_validator("ignore")],
        }
        data, errors = tk.navl_validate(extras, schema)

        if errors:
            raise tk.ValidationError(errors)

        upload = FileStorage(content_length=data["size"])

        max_size = self.storage.max_size
        if max_size:
            utils.ensure_size(upload, max_size)

        result = dict(self.upload(name, upload, data))
        result["size"] = data["size"]

        return result

    def update_multipart_upload(self, upload_data, extras):
        # type: (dict[str, Any], dict[str, Any]) -> dict[str, Any]
        schema = {
            "position": [
                tk.get_validator("not_missing"),
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

        upload = data["upload"]  # type: FileStorage

        expected_size = data["position"] + upload.content_length
        if expected_size > upload_data["size"]:
            raise exceptions.UploadOutOfBoundError(expected_size, upload_data["size"])

        filepath = os.path.join(self.storage.settings["path"], upload_data["filename"])
        with open(filepath, "rb+") as dest:
            dest.seek(data["position"])
            dest.write(upload.stream.read())

        return upload_data

    def complete_multipart_upload(self, upload_data, extras):
        # type: (dict[str, Any], dict[str, Any]) -> FsStorageData
        filepath = os.path.join(self.storage.settings["path"], upload_data["filename"])
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
        # type: (dict[str, Any]) -> bool
        filepath = os.path.join(self.storage.settings["path"], data["filename"])
        if not os.path.exists(filepath):
            return False

        os.remove(filepath)
        return True


class FileSystemStorage(Storage):
    def make_uploader(self):
        return FileSystemUploader(self)

    def make_manager(self):
        return FileSystemManager(self)

    def __init__(self, **settings):
        # type: (**Any) -> None
        path = self.ensure_option(settings, "path")
        if not os.path.exists(path):
            os.makedirs(path)

        super(FileSystemStorage, self).__init__(**settings)


class PublicFileSystemStorage(FileSystemStorage):
    def __init__(self, **settings):
        # type: (**Any) -> None
        self.ensure_option(settings, "public_root")
        super(PublicFileSystemStorage, self).__init__(**settings)
