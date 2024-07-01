from __future__ import annotations

import base64
from typing import IO, Any, Iterable

import requests

from ckan.config.declaration import Declaration, Key

from ckanext.files import exceptions, shared

API_URL = "https://filebin.net"


class FilebinStorage(shared.Storage):
    hidden = True

    @classmethod
    def prepare_settings(cls, settings: dict[str, Any]):
        settings.setdefault("timeout", 10)
        return super().prepare_settings(settings)

    @property
    def bin(self):
        return self.settings["bin"]

    def make_uploader(self):
        return FilebinUploader(self)

    def make_reader(self):
        return FilebinReader(self)

    def make_manager(self):
        return FilebinManager(self)

    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        super().declare_config_options(declaration, key)

        declaration.declare(key.bin).required().set_description("ID of the bin")
        declaration.declare_int(key.timeout, 10).set_description(
            "Timeout of requests to filebin.net",
        )


class FilebinUploader(shared.Uploader):
    storage: FilebinStorage
    required_options = ["bin"]
    capabilities = shared.Capability.CREATE

    def upload(
        self,
        location: str,
        upload: shared.Upload,
        extras: dict[str, Any],
    ) -> shared.FileData:
        filename = self.storage.compute_location(location)
        resp = requests.post(
            f"{API_URL}/{self.storage.bin}/{filename}",
            data=upload.stream,
            timeout=self.storage.settings["timeout"],
        )
        if not resp.ok:
            raise exceptions.UploadError(resp.content)

        info: dict[str, Any] = resp.json()["file"]
        return shared.FileData(
            info["filename"],
            upload.size,
            upload.content_type,
            base64.decodebytes(info["md5"].encode()).decode(),
        )


class FilebinReader(shared.Reader):
    storage: FilebinStorage
    required_options = ["bin"]
    capabilities = (
        shared.Capability.STREAM
        | shared.Capability.PUBLIC_LINK
        | shared.Capability.TEMPORAL_LINK
    )

    def stream(self, data: shared.FileData, extras: dict[str, Any]) -> IO[bytes]:
        resp = requests.get(
            f"{API_URL}/{self.storage.bin}/{data.location}",
            timeout=self.storage.settings["timeout"],
            stream=True,
            headers={"accept": "*/*"},
        )
        if verified := resp.cookies.get("verified"):
            resp = requests.get(
                f"{API_URL}/{self.storage.bin}/{data.location}",
                cookies={"verified": verified},
                timeout=self.storage.settings["timeout"],
                stream=True,
                headers={"accept": "*/*"},
            )

        return resp.raw

    def public_link(self, data: shared.FileData, extras: dict[str, Any]) -> str:
        return f"{API_URL}/{self.storage.bin}/{data.location}"


class FilebinManager(shared.Manager):
    storage: FilebinStorage
    required_options = ["bin"]
    capabilities = (
        shared.Capability.REMOVE | shared.Capability.SCAN | shared.Capability.ANALYZE
    )

    def remove(
        self,
        data: shared.FileData | shared.MultipartData,
        extras: dict[str, Any],
    ) -> bool:
        requests.delete(
            f"{API_URL}/{self.storage.bin}/{data.location}",
            timeout=self.storage.settings["timeout"],
        )
        return True

    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        resp = requests.get(
            f"{API_URL}/{self.storage.bin}",
            headers={"accept": "application/json"},
            timeout=self.storage.settings["timeout"],
        )

        for record in resp.json()["files"]:
            yield record["filename"]

    def analyze(self, location: str, extras: dict[str, Any]) -> shared.FileData:
        resp = requests.get(
            f"{API_URL}/{self.storage.bin}",
            headers={"accept": "application/json"},
            timeout=self.storage.settings["timeout"],
        )
        for record in resp.json()["files"]:
            if record["filename"] == location:
                return shared.FileData(
                    record["filename"],
                    record["size"],
                    record["content-type"],
                    base64.decodebytes(record["md5"].encode()).decode(),
                )

        raise exceptions.MissingFileError(self.storage, location)
