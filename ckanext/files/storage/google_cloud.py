import base64
import os
import re

import requests
import six
from google.cloud.storage import Client
from google.oauth2.service_account import Credentials

import ckan.plugins.toolkit as tk

from ckanext.files import exceptions, types, utils
from ckanext.files.base import Capability, Manager, Storage, Uploader

if six.PY3:
    from typing import Any  # isort: skip # noqa: F401

    GCAdditionalData = types.TypedDict("GCAdditionalData", {"filename": str})

    class GCStorageData(GCAdditionalData, types.MinimalStorageData):
        pass


RE_RANGE = re.compile(r"bytes=(?P<first_byte>\d+)-(?P<last_byte>\d+)")


class GoogleCloudUploader(Uploader):
    storage = None  # type: GoogleCloudStorage # pyright: ignore

    required_options = ["bucket"]
    capabilities = utils.combine_capabilities(
        Capability.CREATE,
        Capability.MULTIPART_UPLOAD,
    )

    def upload(self, name, upload, extras):
        # type: (str, types.Upload, dict[str, Any]) -> GCStorageData
        filename = self.compute_name(name, extras, upload)
        filepath = os.path.join(self.storage.settings["path"], filename)

        client = self.storage.client
        blob = client.bucket(self.storage.settings["bucket"]).blob(filepath)
        blob.upload_from_file(upload.stream)
        filehash = base64.decodebytes(blob.md5_hash.encode()).hex()
        return {
            "filename": filename,
            "content_type": upload.content_type,
            "hash": filehash,
            "size": blob.size or upload.content_length,
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

        filename = self.compute_name(name, extras)
        filepath = os.path.join(self.storage.settings["path"], filename)

        client = self.storage.client
        blob = client.bucket(self.storage.settings["bucket"]).blob(filepath)

        max_size = self.storage.max_size
        if max_size and data["size"] > max_size:
            raise exceptions.LargeUploadError(data["size"], max_size)

        url = blob.create_resumable_upload_session(size=data["size"])  # type: Any

        if not url:
            raise exceptions.UploadError("Cannot initialize session URL")

        return {"session_url": url, "size": data["size"], "uploaded": 0}

    def update_multipart_upload(self, upload_data, extras):
        # type: (dict[str, Any], dict[str, Any]) -> dict[str, Any]
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
        data, errors = tk.navl_validate(extras, schema)

        if errors:
            raise tk.ValidationError(errors)

        if "upload" in data:
            upload = data["upload"]  # type: types.Upload

            first_byte = data.get("position", upload_data["uploaded"])
            last_byte = first_byte + upload.content_length - 1
            size = upload_data["size"]

            if last_byte >= size:
                raise exceptions.UploadOutOfBoundError(last_byte, size)

            if upload.content_length < 256 * 1024 and last_byte < size - 1:
                raise tk.ValidationError(
                    {"upload": ["Only the final part can be smaller than 256KiB"]},
                )

            resp = requests.put(
                upload_data["session_url"],
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
                upload_data["uploaded"] = upload_data["size"]
                upload_data["result"] = resp.json()
                return upload_data

            range_match = RE_RANGE.match(resp.headers["range"])
            if not range_match:
                raise tk.ValidationError(
                    {"upload": ["Invalid response from Google Cloud"]},
                )
            upload_data["uploaded"] = tk.asint(range_match.group("last_byte")) + 1

        elif "uploaded" in data:
            upload_data["uploaded"] = data["uploaded"]

        else:
            raise tk.ValidationError(
                {"upload": ["Either upload or uploaded must be specified"]},
            )

        return upload_data

    def show_multipart_upload(self, upload_data):
        # type: (dict[str, Any]) -> dict[str, Any]
        resp = requests.put(
            upload_data["session_url"],
            headers={
                "content-range": "bytes */{}".format(upload_data["size"]),
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
                upload_data["uploaded"] = tk.asint(range_match.group("last_byte")) + 1
            else:
                upload_data["uploaded"] = 0
        elif resp.status_code in [200, 201]:
            upload_data["uploaded"] = upload_data["size"]
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

        return upload_data

    def complete_multipart_upload(self, upload_data, extras):
        # type: (dict[str, Any], dict[str, Any]) -> GCStorageData
        if upload_data["uploaded"] != upload_data["size"]:
            raise tk.ValidationError(
                {
                    "size": [
                        "Actual filesize {} does not match expected {}".format(
                            upload_data["uploaded"],
                            upload_data["size"],
                        ),
                    ],
                },
            )

        filehash = base64.decodebytes(upload_data["result"]["md5Hash"].encode()).hex()

        return {
            "filename": os.path.relpath(
                upload_data["result"]["name"],
                self.storage.settings["path"],
            ),
            "hash": filehash,
            "content_type": upload_data["result"]["contentType"],
            "size": upload_data["size"],
        }


class GoogleCloudManager(Manager):
    storage = None  # type: GoogleCloudStorage # pyright: ignore
    required_options = ["bucket"]
    capabilities = utils.combine_capabilities(Capability.REMOVE)

    def remove(self, data):
        # type: (dict[str, Any]) -> bool
        filepath = os.path.join(str(self.storage.settings["path"]), data["filename"])
        client = self.storage.client  # type: Client
        blob = client.bucket(self.storage.settings["bucket"]).blob(filepath)
        blob.delete()
        return True


class GoogleCloudStorage(Storage):
    def __init__(self, **settings):
        # type: (**Any) -> None
        settings["path"] = settings.setdefault("path", "").lstrip("/")

        super(GoogleCloudStorage, self).__init__(**settings)

        credentials = None
        credentials_file = settings.get("credentials_file", None)
        if credentials_file:
            credentials = Credentials.from_service_account_file(credentials_file)

        self.client = Client(credentials=credentials)

    def make_uploader(self):
        return GoogleCloudUploader(self)

    def make_manager(self):
        return GoogleCloudManager(self)
