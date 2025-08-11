from __future__ import annotations

import dataclasses
import logging
from typing import Any
from urllib.parse import urlparse, urlunparse

import requests
from typing_extensions import override

from ckanext.files import shared

log = logging.getLogger(__name__)


@dataclasses.dataclass()
class Settings(shared.Settings):
    timeout: int = 5


class Reader(shared.Reader):
    capabilities = shared.Capability.LINK_PERMANENT
    storage: LinkStorage

    @override
    def permanent_link(self, data: shared.FileData, extras: dict[str, Any]) -> str:
        return data.location


class Uploader(shared.Uploader):
    capabilities = shared.Capability.CREATE
    storage: LinkStorage

    @override
    def upload(
        self,
        location: shared.Location,
        upload: shared.Upload,
        extras: dict[str, Any],
    ) -> shared.FileData:
        try:
            url = urlunparse(urlparse(upload.stream.read())).decode()
        except ValueError as err:
            raise shared.exc.ContentError(self, str(err)) from err

        return self.storage.analyze(shared.Location(url))


class Manager(shared.Manager):
    capabilities = shared.Capability.ANALYZE | shared.Capability.REMOVE
    storage: LinkStorage

    @override
    def remove(
        self,
        data: shared.FileData,
        extras: dict[str, Any],
    ) -> bool:
        return True

    @override
    def analyze(self, location: shared.Location, extras: dict[str, Any]) -> shared.FileData:
        resp = requests.head(location, timeout=self.storage.settings.timeout)
        if not resp.ok:
            log.debug("Cannot analyze URL %s: %s", location, resp)

        content_length = resp.headers.get("content-length") or "0"
        size = int(content_length) if content_length.isnumeric() else 0

        content_type = resp.headers.get("content-type") or "application/octet-stream"
        content_type = content_type.split(";", 1)[0]

        hash = resp.headers.get("etag") or ""

        return shared.FileData(location, size, content_type, hash)


class LinkStorage(shared.Storage):
    hidden = True
    settings: Settings  # pyright: ignore[reportIncompatibleVariableOverride]
    SettingsFactory = Settings
    UploaderFactory = Uploader
    ManagerFactory = Manager
    ReaderFactory = Reader

    @override
    @classmethod
    def declare_config_options(
        cls,
        declaration: shared.types.Declaration,
        key: shared.types.Key,
    ):
        super().declare_config_options(declaration, key)
        declaration.declare_int(key.timeout, 5).set_description(
            "Request timeout used when link details fetched during ANALYZE",
        )
