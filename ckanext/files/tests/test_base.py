import hashlib
import uuid
from io import BytesIO

import pytest
from werkzeug.datastructures import FileStorage

from ckanext.files import base, exceptions, utils
from ckanext.files.storage import RedisStorage

from datetime import datetime  # isort: skip # noqa: F401


from faker import Faker  # isort: skip # noqa: F401


class TestStorageFromSettings:
    def test_missing_adapter(self):
        """Unknown udapter causes an exception."""

        with pytest.raises(exceptions.UnknownAdapterError):
            base.storage_from_settings("", {})

    def test_invalid_configuration(self):
        """Wrong configuration causes an exception."""

        with pytest.raises(exceptions.InvalidStorageConfigurationError):
            base.storage_from_settings("", {"type": "files:fs"})

    def test_normal_configuration(self):
        """Valid configuration produces a storage."""

        storage = base.storage_from_settings("", {"type": "files:redis"})
        assert isinstance(storage, RedisStorage)


class TestHasingReader:
    def test_empty_hash(self):
        """Empty reader produces the hash of empty string and doesn't add any
        default bytes.

        """

        reader = base.HashingReader(BytesIO())
        reader.exhaust()

        assert reader.get_hash() == hashlib.md5().hexdigest()

    def test_hash(self, faker):
        # type: (Faker) -> None
        """Reader's hash is based on the stream content."""

        content = faker.binary(100)
        expected = hashlib.md5(content).hexdigest()

        reader = base.HashingReader(BytesIO(content))

        output = b""
        for chunk in reader:
            output += chunk

        assert output == content
        assert reader.get_hash() == expected

    def test_reset(self, faker):
        # type: (Faker) -> None
        """Resetting the reader makes it reusable"""
        stream = BytesIO(faker.binary(100))
        reader = base.HashingReader(stream)

        reader.exhaust()

        first_hash = reader.get_hash()
        assert stream.tell() == 100

        reader.reset()
        assert stream.tell() == 0

        reader.exhaust()
        assert reader.get_hash() == first_hash


class TestOptionCheckeer:
    def test_missing_option(self, faker):
        # type: (Faker) -> None
        """Checker raises an exception if option is missing."""

        with pytest.raises(exceptions.MissingStorageConfigurationError):
            base.OptionChecker.ensure_option({faker.word(): True}, faker.word())

    def test_existing_option(self, faker):
        # type: (Faker) -> None
        """Checker returns the value of existing option"""
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

    def test_missing_option(self, service_class):
        # type: (type[base.StorageService]) -> None
        """Service cannot be initialized without required option."""
        storage = base.Storage()
        with pytest.raises(exceptions.MissingStorageConfigurationError):
            service_class(storage)

    def test_existing_option(self, service_class):
        # type: (type[base.StorageService]) -> None
        """Service works with required options."""
        storage = base.Storage(test=1)
        service_class(storage)


class TestUploader:
    @pytest.fixture()
    def uploader(self):
        return base.Uploader(base.Storage())

    def test_abstract_methods(self, uploader, faker):
        # type: (base.Uploader, Faker) -> None
        """Abstract methods raise exception."""

        with pytest.raises(NotImplementedError):
            uploader.upload(faker.file_name(), FileStorage(), {})

        with pytest.raises(NotImplementedError):
            uploader.initialize_multipart_upload(faker.file_name(), {})

        with pytest.raises(NotImplementedError):
            uploader.show_multipart_upload({})

        with pytest.raises(NotImplementedError):
            uploader.update_multipart_upload({}, {})

        with pytest.raises(NotImplementedError):
            uploader.complete_multipart_upload({}, {})

        with pytest.raises(NotImplementedError):
            uploader.copy({}, "", {})

        with pytest.raises(NotImplementedError):
            uploader.move({}, "", {})

    def test_compute_name_uuid(self, uploader, faker):
        # type: (base.Uploader, Faker) -> None
        """`uuid`(default) name strategy produces valid UUID."""

        extension = faker.file_extension()
        name = faker.file_name(extension=extension)
        result = uploader.compute_name(name, {})

        assert uuid.UUID(result)

    def test_compute_name_uuid_prefix(self, uploader, faker):
        # type: (base.Uploader, Faker) -> None
        """`uuid_prefix` name strategy produces valid UUID."""
        uploader.storage.settings["name_strategy"] = "uuid_prefix"
        extension = faker.file_extension()
        name = faker.file_name(extension=extension)
        result = uploader.compute_name(name, {})
        assert result.endswith(name)
        assert uuid.UUID(result[: -len(name)])

    def test_compute_name_uuid_with_extension(self, uploader, faker):
        # type: (base.Uploader, Faker) -> None
        """`uuid_with_extension` name strategy produces valid UUID."""
        uploader.storage.settings["name_strategy"] = "uuid_with_extension"
        extension = faker.file_extension()
        name = faker.file_name(extension=extension)
        result = uploader.compute_name(name, {})

        assert result.endswith(extension)
        assert uuid.UUID(result[: -len(extension) - 1])

    def test_compute_name_datetime_prefix(self, uploader, faker, files_stopped_time):
        # type: (base.Uploader, Faker, datetime) -> None
        """`datetime_prefix` name strategy produces valid UUID."""
        uploader.storage.settings["name_strategy"] = "datetime_prefix"
        extension = faker.file_extension()
        name = faker.file_name(extension=extension)
        result = uploader.compute_name(name, {})

        assert result == files_stopped_time.isoformat() + name

    def test_compute_name_datetime_with_extension(
        self,
        uploader,
        faker,
        files_stopped_time,
    ):
        # type: (base.Uploader, Faker, datetime) -> None
        """`datetime_with_extension` name strategy produces valid UUID."""
        uploader.storage.settings["name_strategy"] = "datetime_with_extension"
        extension = faker.file_extension()
        name = faker.file_name(extension=extension)
        result = uploader.compute_name(name, {})

        assert result == files_stopped_time.isoformat() + "." + extension

    def test_compute_name_with_wrong_strategy(self, uploader):
        # type: (base.Uploader) -> None
        """`datetime_with_extension` name strategy produces valid UUID."""
        uploader.storage.settings["name_strategy"] = "wrong_strategy"
        with pytest.raises(exceptions.NameStrategyError):
            uploader.compute_name("test", {})


class TestManager:
    @pytest.fixture()
    def manager(self):
        return base.Manager(base.Storage())

    def test_abstract_methods(self, manager):
        # type: (base.Manager) -> None
        """Abstract methods raise exception."""

        with pytest.raises(NotImplementedError):
            manager.remove({})


class TestReader:
    @pytest.fixture()
    def reader(self):
        return base.Reader(base.Storage())

    def test_abstract_methods(self, reader):
        # type: (base.Reader) -> None
        """Abstract methods raise exception."""

        with pytest.raises(NotImplementedError):
            reader.stream({})


class RemovingManager(base.Manager):
    capabilities = utils.combine_capabilities(base.Capability.REMOVE)


class StreamingReader(base.Reader):
    capabilities = utils.combine_capabilities(base.Capability.STREAM)


class SimpleUploader(base.Uploader):
    capabilities = utils.combine_capabilities(base.Capability.CREATE)


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
        storage = Storage()
        assert storage.capabilities == utils.combine_capabilities(
            base.Capability.REMOVE,
            base.Capability.STREAM,
            base.Capability.CREATE,
        )

    def test_settings(self, faker):
        # type: (Faker) -> None
        """Storage keeps all incoming arguments as settings."""

        settings = faker.pydict()
        storage = base.Storage(**settings)
        assert storage.settings == settings

    def test_max_size(self, faker):
        # type: (Faker) -> None
        """Storage has a dedicated property for `max_size` setting."""

        assert base.Storage().max_size == 0

        max_size = faker.pyint()
        assert base.Storage(max_size=max_size).max_size == max_size

    def test_supports(self):
        """Storage can tell whether it supports certain capabilities."""

        storage = Storage()

        assert storage.supports(base.Capability.CREATE)
        assert storage.supports(
            utils.combine_capabilities(
                base.Capability.REMOVE,
                base.Capability.STREAM,
            ),
        )

        assert not storage.supports(base.Capability.MULTIPART_UPLOAD)
        assert not storage.supports(
            utils.combine_capabilities(
                base.Capability.REMOVE,
                base.Capability.MULTIPART_UPLOAD,
            ),
        )

    def test_not_supported_methods(self, faker):
        # type: (Faker) -> None
        with pytest.raises(exceptions.UnsupportedOperationError):
            base.Storage().upload(faker.file_name(), FileStorage(), {})

        with pytest.raises(exceptions.UnsupportedOperationError):
            base.Storage().stream({})

        with pytest.raises(exceptions.UnsupportedOperationError):
            base.Storage().remove({})

        with pytest.raises(exceptions.UnsupportedOperationError):
            base.Storage().copy({}, base.Storage(), "", {})

        with pytest.raises(exceptions.UnsupportedOperationError):
            base.Storage().move({}, base.Storage(), "", {})

    def test_upload_checks_max_size(self, faker):
        # type: (Faker) -> None
        """Storage raises an error if upload exceeds max size."""
        storage = Storage(max_size=10)
        with pytest.raises(exceptions.LargeUploadError):
            storage.upload(
                faker.file_name(),
                FileStorage(BytesIO(faker.binary(20))),
                {},
            )

    def test_not_implemented_methods(self, faker):
        # type: (Faker) -> None
        """Storage raises an error if upload is not implemented."""
        storage = Storage()
        with pytest.raises(NotImplementedError):
            storage.upload(faker.file_name(), FileStorage(), {})

        with pytest.raises(NotImplementedError):
            storage.initialize_multipart_upload(faker.file_name(), {})

        with pytest.raises(NotImplementedError):
            storage.show_multipart_upload({})

        with pytest.raises(NotImplementedError):
            storage.update_multipart_upload({}, {})

        with pytest.raises(NotImplementedError):
            storage.complete_multipart_upload({}, {})

        with pytest.raises(NotImplementedError):
            storage.remove({})

        with pytest.raises(NotImplementedError):
            storage.copy({}, storage, "", {})

        with pytest.raises(NotImplementedError):
            storage.move({}, storage, "", {})
