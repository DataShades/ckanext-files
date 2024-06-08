from __future__ import annotations

import base64
import os
import re
from typing import Any, cast

import requests
from google.api_core.exceptions import Forbidden
from google.cloud.storage import Client
from google.oauth2.service_account import Credentials

import ckan.plugins.toolkit as tk
from ckan.config.declaration import Declaration, Key

from ckanext.files import exceptions
from ckanext.files.base import Manager, Storage, Uploader
from ckanext.files.shared import Capability, FileData, MultipartData, Upload

RE_RANGE = re.compile(r"bytes=(?P<first_byte>\d+)-(?P<last_byte>\d+)")


def decode(value: str) -> str:
    return base64.decodebytes(value.encode()).hex()


class GoogleCloudUploader(Uploader):
    storage: GoogleCloudStorage

    required_options = ["bucket"]
    capabilities = Capability.combine(
        Capability.CREATE,
        Capability.MULTIPART,
    )

    def upload(
        self,
        location: str,
        upload: Upload,
        extras: dict[str, Any],
    ) -> FileData:
        filename = self.storage.compute_location(location, upload, **extras)
        filepath = os.path.join(self.storage.settings["path"], filename)

        client = self.storage.client
        blob = client.bucket(self.storage.settings["bucket"]).blob(filepath)

        blob.upload_from_file(upload.stream)
        filehash = decode(blob.md5_hash)
        return FileData(
            filename,
            blob.size or upload.size,
            upload.type,
            filehash,
        )

    def multipart_start(
        self,
        location: str,
        extras: dict[str, Any],
    ) -> MultipartData:
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

        filename = self.storage.compute_location(location, **extras)
        filepath = os.path.join(self.storage.settings["path"], filename)

        client = self.storage.client
        blob = client.bucket(self.storage.settings["bucket"]).blob(filepath)

        max_size = self.storage.max_size
        if max_size and data["size"] > max_size:
            raise exceptions.LargeUploadError(data["size"], max_size)

        url = cast(
            str,
            blob.create_resumable_upload_session(
                size=data["size"],
                origin=self.storage.settings["resumable_origin"],
            ),
        )

        if not url:
            raise exceptions.UploadError("Cannot initialize session URL")

        return MultipartData(
            filename,
            data["size"],
            storage_data={
                "session_url": url,
                "uploaded": 0,
            },
        )

    def multipart_update(
        self,
        data: MultipartData,
        extras: dict[str, Any],
    ) -> MultipartData:
        schema = {
            "upload": [
                tk.get_validator("ignore_missing"),
                tk.get_validator("files_into_upload"),
            ],
            "position": [
                tk.get_validator("ignore_missing"),
                tk.get_validator("int_validator"),
            ],
            "uploaded": [
                tk.get_validator("ignore_missing"),
                tk.get_validator("int_validator"),
            ],
            "__extras": [tk.get_validator("ignore")],
        }
        valid_data, errors = tk.navl_validate(extras, schema)

        if errors:
            raise tk.ValidationError(errors)

        if "upload" in valid_data:
            upload: Upload = valid_data["upload"]

            first_byte = valid_data.get("position", data.storage_data["uploaded"])
            last_byte = first_byte + upload.size - 1
            size = data.size

            if last_byte >= size:
                raise exceptions.UploadOutOfBoundError(last_byte, size)

            if upload.size < 256 * 1024 and last_byte < size - 1:
                raise tk.ValidationError(
                    {"upload": ["Only the final part can be smaller than 256KiB"]},
                )

            resp = requests.put(
                data.storage_data["session_url"],
                data=upload.stream.read(),
                headers={
                    "content-range": "bytes {}-{}/{}".format(
                        first_byte,
                        last_byte,
                        size,
                    ),
                },
            )

            if not resp.ok:
                raise tk.ValidationError({"upload": [resp.text]})

            if "range" not in resp.headers:
                data.storage_data["uploaded"] = data.size
                data.storage_data["result"] = resp.json()
                return data

            range_match = RE_RANGE.match(resp.headers["range"])
            if not range_match:
                raise tk.ValidationError(
                    {"upload": ["Invalid response from Google Cloud"]},
                )
            data.storage_data["uploaded"] = tk.asint(range_match.group("last_byte")) + 1

        elif "uploaded" in valid_data:
            data.storage_data["uploaded"] = valid_data["uploaded"]

        else:
            raise tk.ValidationError(
                {"upload": ["Either upload or uploaded must be specified"]},
            )

        return data

    def multipart_show(
        self,
        data: MultipartData,
        extras: dict[str, Any],
    ) -> MultipartData:
        resp = requests.put(
            data.storage_data["session_url"],
            headers={
                "content-range": "bytes */{}".format(data.size),
                "content-length": "0",
            },
        )
        if not resp.ok:
            raise tk.ValidationError({"id": [resp.text]})

        if resp.status_code == 308:
            if "range" in resp.headers:
                range_match = RE_RANGE.match(resp.headers["range"])
                if not range_match:
                    raise tk.ValidationError(
                        {
                            "id": [
                                "Invalid response from Google Cloud:"
                                + " missing range header",
                            ],
                        },
                    )
                data.storage_data["uploaded"] = (
                    tk.asint(range_match.group("last_byte")) + 1
                )
            else:
                data.storage_data["uploaded"] = 0
        elif resp.status_code in [200, 201]:
            data.storage_data["uploaded"] = data.size
            data.storage_data["result"] = resp.json()

        else:
            raise tk.ValidationError(
                {
                    "id": [
                        "Invalid response from Google Cloud:"
                        + " unexpected status {}".format(
                            resp.status_code,
                        ),
                    ],
                },
            )

        return data

    def multipart_complete(
        self,
        data: MultipartData,
        extras: dict[str, Any],
    ) -> FileData:
        data = self.multipart_show(data, extras)
        if data.storage_data["uploaded"] != data.size:
            raise tk.ValidationError(
                {
                    "size": [
                        "Actual filesize {} does not match expected {}".format(
                            data.storage_data["uploaded"],
                            data.size,
                        ),
                    ],
                },
            )

        filehash = decode(data.storage_data["result"]["md5Hash"])

        return FileData(
            os.path.relpath(
                data.storage_data["result"]["name"],
                self.storage.settings["path"],
            ),
            data.size,
            data.storage_data["result"]["contentType"],
            filehash,
        )


class GoogleCloudManager(Manager):
    storage: GoogleCloudStorage
    required_options = ["bucket"]
    capabilities = Capability.combine(Capability.REMOVE)

    def remove(self, data: FileData, extras: dict[str, Any]) -> bool:
        filepath = os.path.join(str(self.storage.settings["path"]), data.location)
        client: Client = self.storage.client
        blob = client.bucket(self.storage.settings["bucket"]).blob(filepath)

        try:
            exists = blob.exists()
        except Forbidden as err:
            raise exceptions.PermissionError(
                type(self),
                "exists",
                str(err),
            ) from err

        if exists:
            try:
                blob.delete()
            except Forbidden as err:
                raise exceptions.PermissionError(
                    type(self),
                    "remove",
                    str(err),
                ) from err
            return True
        return False


class GoogleCloudStorage(Storage):
    def __init__(self, **settings: Any):
        settings["path"] = settings.setdefault("path", "").lstrip("/")
        settings.setdefault("resumable_origin", tk.config["ckan.site_url"])

        super(GoogleCloudStorage, self).__init__(**settings)

        credentials = None
        credentials_file = settings.get("credentials_file", None)
        if credentials_file:
            try:
                credentials = Credentials.from_service_account_file(credentials_file)
            except IOError as err:
                raise exceptions.InvalidStorageConfigurationError(
                    type(self),
                    "file `{}` does not exist".format(credentials_file),
                ) from err

        self.client = Client(credentials=credentials)

    def make_uploader(self):
        return GoogleCloudUploader(self)

    def make_manager(self):
        return GoogleCloudManager(self)

    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        super().declare_config_options(declaration, key)
        declaration.declare(key.path, "").set_description(
            "Path to the folder where uploaded data will be stored.",
        )
        declaration.declare(key.bucket).required().set_description(
            "Name of the GCS bucket where uploaded data will be stored.",
        )
        declaration.declare(key.credentials_file).set_description(
            "Path to the credentials file used for authentication by GCS client."
            + "\nIf empty, uses value of GOOGLE_APPLICATION_CREDENTIALS envvar.",
        )
        declaration.declare(
            key.resumable_origin,
            tk.config["ckan.site_url"],
        ).set_description(
            "Value of the Origin header set for resumable upload."
            + "\nIn most cases, keep it the same as CKAN base URL.",
        )
