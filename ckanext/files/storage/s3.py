from __future__ import annotations

import base64
import os
import re
from typing import Any, Iterable

import boto3

import ckan.plugins.toolkit as tk
from ckan.config.declaration import Declaration, Key

from ckanext.files import exceptions
from ckanext.files.base import Manager, Reader, Storage, Uploader
from ckanext.files.shared import Capability, FileData, MultipartData, Upload

RE_RANGE = re.compile(r"bytes=(?P<first_byte>\d+)-(?P<last_byte>\d+)")
HTTP_RESUME = 308


def decode(value: str) -> str:
    return base64.decodebytes(value.encode()).hex()


class S3Reader(Reader):
    storage: S3Storage
    capabilities = Capability.STREAM | Capability.TEMPORAL_LINK

    def stream(self, data: FileData, extras: dict[str, Any]) -> Iterable[bytes]:
        client = self.storage.client
        filepath = os.path.join(self.storage.settings["path"], data.location)

        try:
            obj = client.get_object(
                Bucket=self.storage.settings["bucket"], Key=filepath
            )
        except client.exceptions.NoSuchKey as err:
            raise exceptions.MissingFileError(
                self.storage.settings["name"],
                data.location,
            ) from err

        return obj["Body"]


class S3Uploader(Uploader):
    storage: S3Storage

    required_options = ["bucket"]
    capabilities = Capability.CREATE | Capability.MULTIPART

    def upload(
        self,
        location: str,
        upload: Upload,
        extras: dict[str, Any],
    ) -> FileData:
        filename = self.storage.compute_location(location, upload, **extras)
        filepath = os.path.join(self.storage.settings["path"], filename)

        client = self.storage.client
        obj = client.put_object(
            Bucket=self.storage.settings["bucket"], Key=filepath, Body=upload.stream
        )

        filehash = obj["ETag"].strip('"')

        return FileData(
            filename,
            upload.size,
            upload.content_type,
            filehash,
        )

    def multipart_start(
        self,
        location: str,
        data: MultipartData,
        extras: dict[str, Any],
    ) -> MultipartData:
        filename = self.storage.compute_location(location, **extras)

        max_size = self.storage.max_size
        if max_size and data.size > max_size:
            raise exceptions.LargeUploadError(data.size, max_size)

        filepath = os.path.join(self.storage.settings["path"], filename)
        client = self.storage.client
        obj = client.create_multipart_upload(
            Bucket=self.storage.settings["bucket"],
            Key=filepath,
            ContentType=data.content_type,
        )

        data.location = filename
        data.storage_data = dict(
            data.storage_data,
            upload_id=obj["UploadId"],
            uploaded=0,
            part_number=1,
            upload_url=self._presigned_part(filepath, obj["UploadId"], 1),
            etags={},
        )
        return data

    def _presigned_part(self, key: str, upload_id: str, part_number: int):
        return self.storage.client.generate_presigned_url(
            "upload_part",
            Params={
                "Bucket": self.storage.settings["bucket"],
                "Key": key,
                "UploadId": upload_id,
                "PartNumber": part_number,
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
            # "part_number": [
            #     tk.get_validator("ignore_missing"),
            #     tk.get_validator("int_validator"),
            # ],
            "etag": [
                tk.get_validator("ignore_missing"),
                tk.get_validator("unicode_safe"),
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

        filepath = os.path.join(self.storage.settings["path"], data.location)
        if "upload" in valid_data:
            upload: Upload = valid_data["upload"]

            first_byte = data.storage_data["uploaded"]
            last_byte = first_byte + upload.size
            size = data.size

            if last_byte > size:
                raise exceptions.UploadOutOfBoundError(last_byte, size)

            if upload.size < 1024 * 1024 * 5 and last_byte < size:
                raise tk.ValidationError(
                    {"upload": ["Only the final part can be smaller than 5MiB"]},
                )

            resp = self.storage.client.upload_part(
                Bucket=self.storage.settings["bucket"],
                Key=filepath,
                UploadId=data.storage_data["upload_id"],
                PartNumber=data.storage_data["part_number"],
                Body=upload.stream,
            )

            etag = resp["ETag"].strip('"')
            data.storage_data["uploaded"] = data.storage_data["uploaded"] + upload.size

        elif "etag" in valid_data:
            etag = valid_data["etag"].strip('"')
            data.storage_data["uploaded"] = data.storage_data[
                "uploaded"
            ] + valid_data.get("uploaded", 0)

        else:
            raise tk.ValidationError(
                {"upload": ["Either upload or etag must be specified"]}
            )

        data.storage_data["etags"][data.storage_data["part_number"]] = etag
        data.storage_data["part_number"] = data.storage_data["part_number"] + 1

        data.storage_data["upload_url"] = self._presigned_part(
            filepath, data.storage_data["upload_id"], data.storage_data["part_number"]
        )

        return data

    def multipart_complete(
        self,
        data: MultipartData,
        extras: dict[str, Any],
    ) -> FileData:
        filepath = os.path.join(self.storage.settings["path"], data.location)

        result = self.storage.client.complete_multipart_upload(
            Bucket=self.storage.settings["bucket"],
            Key=filepath,
            UploadId=data.storage_data["upload_id"],
            MultipartUpload={
                "Parts": [
                    {"PartNumber": int(num), "ETag": tag}
                    for num, tag in data.storage_data["etags"].items()
                ]
            },
        )

        obj = self.storage.client.get_object(
            Bucket=self.storage.settings["bucket"], Key=result["Key"]
        )

        return FileData(
            os.path.relpath(
                result["Key"],
                self.storage.settings["path"],
            ),
            obj["ContentLength"],
            obj["ContentType"],
            obj["ETag"].strip('"'),
        )


class S3Manager(Manager):
    storage: S3Storage
    required_options = ["bucket"]
    capabilities = Capability.REMOVE | Capability.ANALYZE

    def remove(self, data: FileData | MultipartData, extras: dict[str, Any]) -> bool:
        if isinstance(data, MultipartData):
            return False

        filepath = os.path.join(str(self.storage.settings["path"]), data.location)
        client = self.storage.client

        # TODO: check if file exists before removing to return correct status
        client.delete_object(Bucket=self.storage.settings["bucket"], Key=filepath)

        return True

    def analyze(self, location: str, extras: dict[str, Any]) -> FileData:
        """Return all details about location."""
        filepath = os.path.join(str(self.storage.settings["path"]), location)
        client = self.storage.client

        try:
            obj = client.get_object(
                Bucket=self.storage.settings["bucket"], Key=filepath
            )
        except client.exceptions.NoSuchKey as err:
            raise exceptions.MissingFileError(self.storage, filepath) from err

        return FileData(
            location,
            size=obj["ContentLength"],
            content_type=obj["ContentType"],
            hash=obj["ETag"].strip('"'),
        )


class S3Storage(Storage):
    hidden = True

    @classmethod
    def prepare_settings(cls, settings: dict[str, Any]):
        settings.setdefault("path", "")
        settings.setdefault("key", None)
        settings.setdefault("secret", None)
        settings.setdefault("region", None)
        settings.setdefault("endpoint", None)
        return super().prepare_settings(settings)

    def __init__(self, settings: Any):
        settings["path"] = settings["path"].lstrip("/")

        self.client = boto3.client(
            "s3",
            aws_access_key_id=settings["key"],
            aws_secret_access_key=settings["secret"],
            region_name=settings["region"],
            endpoint_url=settings["endpoint"],
        )

        super().__init__(settings)

    def make_uploader(self):
        return S3Uploader(self)

    def make_reader(self):
        return S3Reader(self)

    def make_manager(self):
        return S3Manager(self)

    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        super().declare_config_options(declaration, key)

        declaration.declare(key.bucket).required().set_description(
            "Name of the S3 bucket where uploaded data will be stored.",
        )
        declaration.declare(key.path, "").set_description(
            "Path to the folder where uploaded data will be stored.",
        )
        declaration.declare(key.key).set_description("The access key for AWS account.")
        declaration.declare(key.secret).set_description(
            "The secret key for AWS account."
        )

        declaration.declare(key.region).set_description(
            "The AWS Region used in instantiating the client."
        )

        declaration.declare(key.endpoint).set_description(
            "The complete URL to use for the constructed client."
        )
