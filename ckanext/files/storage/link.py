from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse, urlunparse

import requests

from ckanext.files import shared

log = logging.getLogger(__name__)


class LinkStorage(shared.Storage):
    hidden = True

    def make_reader(self):
        return LinkReader(self)

    def make_uploader(self):
        return LinkUploader(self)

    def make_manager(self):
        return LinkManager(self)

    @classmethod
    def prepare_settings(cls, settings: dict[str, Any]):
        settings.setdefault("timeout", 5)
        return super().prepare_settings(settings)

    @classmethod
    def declare_config_options(
        cls,
        declaration: shared.types.Declaration,
        key: shared.types.Key,
    ):
        declaration.declare_int(key.timeout, 5).set_description(
            "Request timeout used when link details fetched during ANALYZE",
        )
        super().declare_config_options(declaration, key)


class LinkReader(shared.Reader):
    capabilities = shared.Capability.PUBLIC_LINK

    def public_link(self, data: shared.FileData, extras: dict[str, Any]) -> str:
        return data.location


class LinkUploader(shared.Uploader):
    capabilities = shared.Capability.CREATE

    def upload(
        self,
        location: str,
        upload: shared.Upload,
        extras: dict[str, Any],
    ) -> shared.FileData:
        try:
            url = urlunparse(urlparse(upload.stream.read())).decode()
        except ValueError as err:
            raise shared.exc.ContentError(self, str(err)) from err

        return self.storage.analyze(url)


class LinkManager(shared.Manager):
    capabilities = shared.Capability.ANALYZE | shared.Capability.REMOVE

    def remove(
        self,
        data: shared.FileData | shared.MultipartData,
        extras: dict[str, Any],
    ) -> bool:
        return True

    def analyze(self, location: str, extras: dict[str, Any]) -> shared.FileData:
        resp = requests.head(location, timeout=self.storage.settings["timeout"])
        if not resp.ok:
            log.debug("Cannot analyze URL %s: %s", location, resp)

        content_length = resp.headers.get("content-length") or "0"
        size = int(content_length) if content_length.isnumeric() else 0

        content_type = resp.headers.get("content-type") or "application/octet-stream"
        content_type = content_type.split(";", 1)[0]

        hash = resp.headers.get("etag") or ""

        return shared.FileData(location, size, content_type, hash)
