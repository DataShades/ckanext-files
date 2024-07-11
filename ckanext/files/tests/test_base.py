from __future__ import annotations

import uuid
from datetime import datetime
from io import BytesIO

import pytest
from faker import Faker

from ckanext.files import base, exceptions
from ckanext.files.shared import Capability, FileData, MultipartData, make_upload
from ckanext.files.storage import RedisStorage


class TestMakeStorage:
    def test_missing_adapter(self):
        """Unknown udapter causes an exception."""
        with pytest.raises(exceptions.UnknownAdapterError):
            base.make_storage("", {})

    def test_invalid_configuration(self):
        """Wrong configuration causes an exception."""
        with pytest.raises(exceptions.InvalidStorageConfigurationError):
            base.make_storage("", {"type": "files:fs"}, True)

    def test_normal_configuration(self):
        """Valid configuration produces a storage."""
        storage = base.make_storage("", {"type": "files:redis"}, True)
        assert isinstance(storage, RedisStorage)


class TestOptionCheckeer:
    def test_missing_option(self, faker: Faker):
        """Checker raises an exception if option is missing."""
        with pytest.raises(exceptions.MissingStorageConfigurationError):
            base.OptionChecker.ensure_option({faker.word(): True}, faker.word())

    def test_existing_option(self, faker: Faker):
        """Checker returns the value of existing option."""
        option = faker.word()
        value = faker.word()

        result = base.OptionChecker.ensure_option({option: value}, option)
        assert result == value


class TestStorageService:
    @pytest.fixture()
    def service_class(self):
        class Service(base.StorageService):
            required_options = ["test"]

        return Service

    def test_missing_option(self, service_class: type[base.StorageService]):
        """Service cannot be initialized without required option."""
        storage = base.Storage({})
        with pytest.raises(exceptions.MissingStorageConfigurationError):
            service_class(storage)

    def test_existing_option(self, service_class: type[base.StorageService]):
        """Service works with required options."""
        storage = base.Storage({"test": 1})
        service_class(storage)


class TestUploader:
    @pytest.fixture()
    def uploader(self):
        return base.Uploader(base.Storage({}))

    def test_abstract_methods(self, uploader: base.Uploader, faker: Faker):
        """Abstract methods raise exception."""
        with pytest.raises(NotImplementedError):
            uploader.upload(faker.file_name(), make_upload(b""), {})

        with pytest.raises(NotImplementedError):
            uploader.multipart_start(faker.file_name(), MultipartData(), {})

        with pytest.raises(NotImplementedError):
            uploader.multipart_refresh(MultipartData(), {})

        with pytest.raises(NotImplementedError):
            uploader.multipart_update(MultipartData(), {})

        with pytest.raises(NotImplementedError):
            uploader.multipart_complete(MultipartData(), {})


class TestManager:
    @pytest.fixture()
    def manager(self):
        return base.Manager(base.Storage({}))

    def test_abstract_methods(self, manager: base.Manager):
        """Abstract methods raise exception."""
        with pytest.raises(NotImplementedError):
            manager.remove(FileData(""), {})


class TestReader:
    @pytest.fixture()
    def reader(self):
        return base.Reader(base.Storage({}))

    def test_abstract_methods(self, reader: base.Reader):
        """Abstract methods raise exception."""
        with pytest.raises(NotImplementedError):
            reader.stream(FileData(""), {})


class RemovingManager(base.Manager):
    capabilities = Capability.REMOVE


class StreamingReader(base.Reader):
    capabilities = Capability.STREAM


class SimpleUploader(base.Uploader):
    capabilities = Capability.CREATE


class Storage(base.Storage):
    def make_reader(self):
        return StreamingReader(self)

    def make_uploader(self):
        return SimpleUploader(self)

    def make_manager(self):
        return RemovingManager(self)


class TestStorage:
    def test_inherited_capabilities(self):
        """Storage combine capabilities of its services."""
        storage = Storage({})
        assert storage.capabilities == (
            Capability.REMOVE | Capability.STREAM | Capability.CREATE
        )

    def test_settings(self, faker: Faker):
        """Storage keeps all incoming arguments as settings."""
        settings = faker.pydict()

        storage = base.Storage(settings)
        assert storage.settings == settings

        storage = base.Storage(base.Storage.prepare_settings(settings))
        expected = dict(
            {"supported_types": [], "max_size": 0, "override_existing": False},
            **settings,
        )
        assert storage.settings == expected

    def test_max_size(self, faker: Faker):
        """Storage has a dedicated property for `max_size` setting."""
        assert base.Storage(base.Storage.prepare_settings({})).max_size == 0

        max_size = faker.pyint()
        assert (
            base.Storage(
                base.Storage.prepare_settings({"max_size": max_size}),
            ).max_size
            == max_size
        )

    def test_supports(self):
        """Storage can tell whether it supports certain capabilities."""
        storage = Storage({})

        assert storage.supports(Capability.CREATE)
        assert storage.supports(Capability.REMOVE | Capability.STREAM)

        assert not storage.supports(Capability.MULTIPART)
        assert not storage.supports(Capability.REMOVE | Capability.MULTIPART)

    def test_not_supported_methods(self, faker: Faker):
        with pytest.raises(exceptions.UnsupportedOperationError):
            base.Storage(base.Storage.prepare_settings({})).upload(
                faker.file_name(),
                make_upload(b""),
            )

        with pytest.raises(exceptions.UnsupportedOperationError):
            base.Storage(base.Storage.prepare_settings({})).stream(FileData(""))

        with pytest.raises(exceptions.UnsupportedOperationError):
            base.Storage(base.Storage.prepare_settings({})).remove(FileData(""))

        with pytest.raises(exceptions.UnsupportedOperationError):
            base.Storage(base.Storage.prepare_settings({})).copy(
                FileData(""),
                base.Storage(base.Storage.prepare_settings({})),
                "",
            )

        with pytest.raises(exceptions.UnsupportedOperationError):
            base.Storage(base.Storage.prepare_settings({})).move(
                FileData(""),
                base.Storage(base.Storage.prepare_settings({})),
                "",
            )

    def test_upload_checks_max_size(self, faker: Faker):
        """Storage raises an error if upload exceeds max size."""
        storage = Storage(base.Storage.prepare_settings({"max_size": 10}))
        with pytest.raises(exceptions.LargeUploadError):
            storage.upload(faker.file_name(), make_upload(BytesIO(faker.binary(20))))

    def test_not_implemented_methods(self, faker: Faker):
        """Storage raises an error if upload is not implemented."""
        storage = Storage(base.Storage.prepare_settings({}))
        with pytest.raises(NotImplementedError):
            storage.upload(faker.file_name(), make_upload(b""))

        with pytest.raises(NotImplementedError):
            storage.multipart_start(faker.file_name(), MultipartData())

        with pytest.raises(NotImplementedError):
            storage.multipart_refresh(MultipartData())

        with pytest.raises(NotImplementedError):
            storage.multipart_update(MultipartData())

        with pytest.raises(NotImplementedError):
            storage.multipart_complete(MultipartData())

        with pytest.raises(NotImplementedError):
            storage.remove(FileData(""))

        with pytest.raises(NotImplementedError):
            storage.copy(FileData(""), storage, "")

        with pytest.raises(NotImplementedError):
            storage.move(FileData(""), storage, "")

    def test_compute_location_uuid(self, faker: Faker):
        """`uuid`(default) name strategy produces valid UUID."""
        storage = Storage(base.Storage.prepare_settings({}))

        extension = faker.file_extension()
        name = faker.file_name(extension=extension)
        result = storage.compute_location(name)

        assert uuid.UUID(result)

    def test_compute_location_uuid_prefix(self, faker: Faker):
        """`uuid_prefix` name strategy produces valid UUID."""
        storage = Storage(base.Storage.prepare_settings({}))

        storage.settings["location_strategy"] = "uuid_prefix"
        extension = faker.file_extension()
        name = faker.file_name(extension=extension)
        result = storage.compute_location(name)
        assert result.endswith(name)
        assert uuid.UUID(result[: -len(name)])

    def test_compute_location_uuid_with_extension(self, faker: Faker):
        """`uuid_with_extension` name strategy produces valid UUID."""
        storage = Storage(base.Storage.prepare_settings({}))
        storage.settings["location_strategy"] = "uuid_with_extension"
        extension = faker.file_extension()
        name = faker.file_name(extension=extension)
        result = storage.compute_location(name)

        assert result.endswith(extension)
        assert uuid.UUID(result[: -len(extension) - 1])

    def test_compute_location_datetime_prefix(
        self,
        faker: Faker,
        files_stopped_time: datetime,
    ):
        """`datetime_prefix` name strategy produces valid UUID."""
        storage = Storage(base.Storage.prepare_settings({}))
        storage.settings["location_strategy"] = "datetime_prefix"
        extension = faker.file_extension()
        name = faker.file_name(extension=extension)
        result = storage.compute_location(name)

        assert result == files_stopped_time.isoformat() + name

    def test_compute_location_datetime_with_extension(
        self,
        faker: Faker,
        files_stopped_time: datetime,
    ):
        """`datetime_with_extension` name strategy produces valid UUID."""
        storage = Storage(base.Storage.prepare_settings({}))
        storage.settings["location_strategy"] = "datetime_with_extension"
        extension = faker.file_extension()
        name = faker.file_name(extension=extension)
        result = storage.compute_location(name)

        assert result == files_stopped_time.isoformat() + "." + extension

    def test_compute_location_with_wrong_strategy(self):
        """`datetime_with_extension` name strategy produces valid UUID."""
        storage = Storage(base.Storage.prepare_settings({}))
        storage.settings["location_strategy"] = "wrong_strategy"
        with pytest.raises(exceptions.NameStrategyError):
            storage.compute_location("test")
