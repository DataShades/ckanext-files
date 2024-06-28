from __future__ import annotations

from typing import IO, Any, Iterable, cast

import opendal

from ckan.config.declaration import Declaration, Key

from ckanext.files import shared


class OpenDalStorage(shared.Storage):
    def make_uploader(self):
        return OpenDalUploader(self)

    def make_reader(self):
        return OpenDalReader(self)

    def make_manager(self):
        return OpenDalManager(self)

    @classmethod
    def prepare_settings(cls, settings: dict[str, Any]):
        settings.setdefault("params", {})
        return super().prepare_settings(settings)

    def __init__(self, settings: Any):
        scheme = self.ensure_option(settings, "scheme")
        params = self.ensure_option(settings, "params")

        try:
            self.operator = opendal.Operator(scheme, **params)
        except opendal.exceptions.ConfigInvalid as err:  # type: ignore
            raise shared.exc.InvalidStorageConfigurationError(
                type(self),
                str(err),
            ) from err

        super().__init__(settings)

    def compute_capabilities(self) -> shared.Capability:
        cluster = super().compute_capabilities()
        capabilities = self.operator.capability()

        if not capabilities.delete:
            cluster = cluster.exclude(shared.Capability.REMOVE)

        if not capabilities.list:
            cluster = cluster.exclude(shared.Capability.SCAN)

        if not capabilities.write:
            cluster = cluster.exclude(shared.Capability.CREATE)

        if not capabilities.read:
            cluster = cluster.exclude(shared.Capability.STREAM)

        return cluster

    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        super().declare_config_options(declaration, key)
        declaration.declare(key.scheme).required().set_description(
            "OpenDAL service type. Check available services at"
            + "  https://docs.rs/opendal/latest/opendal/services/index.html",
        )
        declaration.declare(key.params).set_description(
            "JSON object with parameters passed directly to OpenDAL operator.",
        ).set_validators("default({}) convert_to_json_if_string dict_only")


class OpenDalUploader(shared.Uploader):
    storage: OpenDalStorage
    capabilities = shared.Capability.CREATE

    def upload(
        self,
        location: str,
        upload: shared.Upload,
        extras: dict[str, Any],
    ) -> shared.FileData:
        safe_location = self.storage.compute_location(location)
        reader = upload.hashing_reader()
        with self.storage.operator.open(safe_location, "wb") as dest:
            for chunk in reader:
                dest.write(chunk)

        return shared.FileData(
            safe_location,
            upload.size,
            upload.content_type,
            reader.get_hash(),
        )


class OpenDalReader(shared.Reader):
    storage: OpenDalStorage
    capabilities = shared.Capability.STREAM

    def stream(self, data: shared.FileData, extras: dict[str, Any]) -> IO[bytes]:
        return cast(Any, self.storage.operator.open(data.location, "rb"))


class OpenDalManager(shared.Manager):
    storage: OpenDalStorage

    capabilities = shared.Capability.REMOVE | shared.Capability.SCAN

    def remove(
        self,
        data: shared.FileData | shared.MultipartData,
        extras: dict[str, Any],
    ) -> bool:
        self.storage.operator.delete(data.location)
        return True

    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        for entry in self.storage.operator.scan(""):
            stat = self.storage.operator.stat(entry.path)
            if opendal.EntryMode.is_file(stat.mode):
                yield entry.path
