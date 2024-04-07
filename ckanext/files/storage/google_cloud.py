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

GCAdditionalData = types.TypedDict("GCAdditionalData", {})


class GCStorageData(GCAdditionalData, types.MinimalStorageData):
    pass


RE_RANGE = re.compile(r"bytes=(?P<first_byte>\d+)-(?P<last_byte>\d+)")


def decode(value):
    # type: (str) -> str
    if six.PY3:
        return base64.decodebytes(value.encode()).hex()

    return base64.decodestring(value.encode()).encode("hex")  # type: ignore


class GoogleCloudUploader(Uploader):
    storage = None  # type: GoogleCloudStorage # pyright: ignore

    required_options = ["bucket"]
    capabilities = utils.combine_capabilities(
        Capability.CREATE,
        Capability.MULTIPART_UPLOAD,
    )

    def upload(self, name, upload, extras):
        # type: (str, types.Upload, dict[str, types.Any]) -> GCStorageData
        filename = self.compute_name(name, extras, upload)
        filepath = os.path.join(self.storage.settings["path"], filename)

        client = self.storage.client
        blob = client.bucket(self.storage.settings["bucket"]).blob(filepath)

        blob.upload_from_file(upload.stream)
        filehash = decode(blob.md5_hash)
        return {
            "filename": filename,
            "content_type": upload.content_type,
            "hash": filehash,
            "size": blob.size or upload.content_length,
        }

    def initialize_multipart_upload(self, name, extras):
        # type: (str, dict[str, types.Any]) -> dict[str, types.Any]

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

        url = blob.create_resumable_upload_session(
            size=data["size"],
            origin=self.storage.settings["resumable_origin"],
        )  # type: types.Any

        if not url:
            raise exceptions.UploadError("Cannot initialize session URL")

        return {
            "session_url": url,
            "size": data["size"],
            "uploaded": 0,
            "filename": filename,
        }

    def update_multipart_upload(self, upload_data, extras):
        # type: (dict[str, types.Any], dict[str, types.Any]) -> dict[str, types.Any]
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
        # type: (dict[str, types.Any]) -> dict[str, types.Any]

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
            upload_data["result"] = resp.json()

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
        # type: (dict[str, types.Any], dict[str, types.Any]) -> GCStorageData
        upload_data = self.show_multipart_upload(upload_data)
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

        filehash = decode(upload_data["result"]["md5Hash"])

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
        # type: (dict[str, types.Any]) -> bool

        filepath = os.path.join(str(self.storage.settings["path"]), data["filename"])
        client = self.storage.client  # type: Client
        blob = client.bucket(self.storage.settings["bucket"]).blob(filepath)
        if blob.exists():
            blob.delete()
            return True
        return False


class GoogleCloudStorage(Storage):
    def __init__(self, **settings):
        # type: (**types.Any) -> None
        settings["path"] = settings.setdefault("path", "").lstrip("/")
        settings.setdefault("resumable_origin", tk.config["ckan.site_url"])

        super(GoogleCloudStorage, self).__init__(**settings)

        credentials = None
        credentials_file = settings.get("credentials_file", None)
        if credentials_file:
            try:
                credentials = Credentials.from_service_account_file(credentials_file)
            except IOError:
                raise exceptions.InvalidStorageConfigurationError(  # noqa: B904
                    type(self),
                    "file `{}` does not exist".format(credentials_file),
                )

        self.client = Client(credentials=credentials)

    def make_uploader(self):
        return GoogleCloudUploader(self)

    def make_manager(self):
        return GoogleCloudManager(self)

    @classmethod
    def declare_config_options(cls, declaration, key):
        # type: (types.Declaration, types.Key) -> None
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
