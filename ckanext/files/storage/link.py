"""Link storage implementation for CKAN file storage extension.

This storage backend allows CKAN to handle files that are represented by URLs.
It provides capabilities to analyze link metadata, create file entries from links,
and generate permanent links to the files.
"""

from __future__ import annotations

import dataclasses
import logging
from typing import Any
from urllib.parse import urlparse, urlunparse

import requests
from typing_extensions import override

from ckanext.files import shared

log = logging.getLogger(__name__)


class Reader(shared.Reader):
    capabilities = shared.Capability.LINK_PERMANENT
    storage: LinkStorage

    @override
    def permanent_link(self, data: shared.FileData, extras: dict[str, Any]) -> str:
        return data.storage_data.get("url", data.location)


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
            parsed = urlparse(upload.stream.read().decode())
        except ValueError as err:
            raise shared.exc.ContentError(self, str(err)) from err

        protocols = self.storage.settings.protocols
        if protocols and parsed.scheme not in protocols:
            msg = f"{parsed.scheme} protocol is not supported"
            raise shared.exc.ContentError(self, msg)

        domains = self.storage.settings.domains
        if domains and parsed.hostname not in domains:
            msg = f"Domain {parsed.hostname} is not allowed"
            raise shared.exc.ContentError(self, msg)

        url = urlunparse(parsed)
        resp = requests.head(url, timeout=self.storage.settings.timeout)
        if not resp.ok:
            log.debug("Cannot analyze URL %s: %s", url, resp)

        content_length = resp.headers.get("content-length") or "0"
        size = int(content_length) if content_length.isnumeric() else 0

        content_type = resp.headers.get("content-type") or "application/octet-stream"
        content_type = content_type.split(";", 1)[0]

        hash = resp.headers.get("etag") or ""

        return shared.FileData(location, size, content_type, hash, storage_data={"url": url})


@dataclasses.dataclass()
class Settings(shared.Settings):
    timeout: int = 5
    protocols: list[str] = dataclasses.field(default_factory=list)
    domains: list[str] = dataclasses.field(default_factory=list)


class LinkStorage(shared.Storage):
    hidden = True
    settings: Settings  # pyright: ignore[reportIncompatibleVariableOverride]
    SettingsFactory = Settings
    UploaderFactory = Uploader
    ReaderFactory = Reader

    @override
    @classmethod
    def declare_config_options(
        cls,
        declaration: shared.types.Declaration,
        key: shared.types.Key,
    ):
        super().declare_config_options(declaration, key)
        declaration.declare_int(key.timeout, Settings.timeout).set_description(
            "Request timeout used when link details fetched during upload.",
        )
        declaration.declare_list(key.protocols, None).set_description(
            "List of allowed protocols for link uploads. Empty list means all protocols are allowed.",
        )
        declaration.declare_list(key.domains, None).set_description(
            "List of allowed hostnames for link uploads. Empty list means all domains are allowed.",
        )
