from __future__ import annotations

from typing import Any, Iterable

from libcloud.base import DriverType, get_driver
from libcloud.common.types import LibcloudError
from libcloud.storage.base import Container, StorageDriver
from libcloud.storage.types import ContainerDoesNotExistError, ObjectDoesNotExistError

from ckan.config.declaration import Declaration, Key

from ckanext.files import shared

PROVIDERS_URL = (
    "https://libcloud.readthedocs.io/en/stable/storage/"
    + "supported_providers.html#provider-matrix"
)

get_driver: Any


class LibCloudStorage(shared.Storage):
    driver: StorageDriver
    container: Container

    @classmethod
    def prepare_settings(cls, settings: dict[str, Any]):
        settings.setdefault("secret", None)
        settings.setdefault("params", {})
        return super().prepare_settings(settings)

    def __init__(self, settings: Any):
        provider = self.ensure_option(settings, "provider")
        key = self.ensure_option(settings, "key")
        container = self.ensure_option(settings, "container")
        secret = self.ensure_option(settings, "secret")
        params = self.ensure_option(settings, "params")

        try:
            factory = get_driver(DriverType.STORAGE, provider)
        except AttributeError as err:
            raise shared.exc.InvalidStorageConfigurationError(
                type(self),
                str(err),
            ) from err

        self.driver = factory(key, secret, **params)

        try:
            self.container = self.driver.get_container(container)
        except ContainerDoesNotExistError as err:
            msg = f"Container {container} does not exist"
            raise shared.exc.InvalidStorageConfigurationError(type(self), msg) from err
        except LibcloudError as err:
            raise shared.exc.InvalidStorageConfigurationError(
                type(self),
                str(err),
            ) from err

        super().__init__(settings)

    def make_uploader(self):
        return LibCloudUploader(self)

    def make_reader(self):
        return LibCloudReader(self)

    def make_manager(self):
        return LibCloudManager(self)

    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        super().declare_config_options(declaration, key)
        declaration.declare(key.provider).required().set_description(
            "apache-libcloud storage provider. List of providers available at"
            + f" {PROVIDERS_URL} . Use upper-cased value from Provider Constant column",
        )
        declaration.declare(key.key).required().set_description("API key or username")
        declaration.declare(key.secret).set_description("Secret password")
        declaration.declare(key.params).set_description(
            "JSON object with additional parameters"
            + " passed directly to storage constructor.",
        ).set_validators("default({}) convert_to_json_if_string dict_only")
        declaration.declare(key.container).required().set_description(
            "Name of the container(bucket)",
        )


class LibCloudUploader(shared.Uploader):
    storage: LibCloudStorage
    capabilities = shared.Capability.CREATE

    def upload(
        self,
        location: str,
        upload: shared.Upload,
        extras: dict[str, Any],
    ) -> shared.FileData:
        safe_location = self.storage.compute_location(location)

        result = self.storage.container.upload_object_via_stream(
            iter(upload.stream),
            safe_location,
            extra={"content_type": upload.content_type},
        )

        return shared.FileData(
            result.name,
            result.size,
            upload.content_type,
            result.hash.strip('"'),
        )


class LibCloudReader(shared.Reader):
    storage: LibCloudStorage
    capabilities = shared.Capability.STREAM | shared.Capability.TEMPORAL_LINK

    def stream(self, data: shared.FileData, extras: dict[str, Any]) -> Iterable[bytes]:
        try:
            obj = self.storage.container.get_object(data.location)
        except ObjectDoesNotExistError as err:
            raise shared.exc.MissingFileError(
                self.storage.settings["name"],
                data.location,
            ) from err

        return obj.as_stream()


class LibCloudManager(shared.Manager):
    storage: LibCloudStorage
    capabilities = shared.Capability.SCAN | shared.Capability.REMOVE

    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        for item in self.storage.container.iterate_objects():
            yield item.name

    def remove(
        self,
        data: shared.FileData | shared.MultipartData,
        extras: dict[str, Any],
    ) -> bool:
        try:
            obj = self.storage.container.get_object(data.location)
        except ObjectDoesNotExistError:
            return False
        return self.storage.container.delete_object(obj)
