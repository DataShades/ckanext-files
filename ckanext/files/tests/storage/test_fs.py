import hashlib
import os
from io import BytesIO
from uuid import UUID

import pytest
from werkzeug.datastructures import FileStorage

import ckan.plugins.toolkit as tk

from ckanext.files import exceptions
from ckanext.files.storage import fs

from faker import Faker  # isort: skip # noqa: F401


@pytest.fixture()
def storage(clean_redis, tmp_path):
    # type: (object, object) -> fs.FileSystemStorage
    return fs.FileSystemStorage(name="test", path=str(tmp_path))


class TestUploader:
    def test_key(self, storage):
        # type: (fs.FileSystemStorage) -> None
        result = storage.upload("", FileStorage(), {})

        assert UUID(result["filename"])
        assert result["size"] == 0

        filepath = os.path.join(storage.settings["path"], result["filename"])

        assert os.path.exists(filepath)
        assert os.path.getsize(filepath) == 0

    def test_content(self, storage, faker):
        # type: (fs.FileSystemStorage, Faker) -> None
        content = faker.binary(100)
        result = storage.upload("", FileStorage(BytesIO(content)), {})

        assert result["size"] == 100

        filepath = os.path.join(storage.settings["path"], result["filename"])
        assert open(filepath, "rb").read() == content

    def test_hash(self, storage, faker):
        # type: (fs.FileSystemStorage, Faker) -> None
        result = storage.upload("", FileStorage(), {})
        assert result["hash"] == hashlib.md5().hexdigest()

        content = faker.binary(100)
        result = storage.upload("", FileStorage(BytesIO(content)), {})
        assert result["hash"] == hashlib.md5(content).hexdigest()


@pytest.mark.usefixtures("with_plugins")
class TestMultipartUploader:
    def test_initialization_invalid(self, storage, faker):
        # type: (fs.FileSystemStorage, Faker) -> None
        with pytest.raises(tk.ValidationError):
            storage.initialize_multipart_upload(faker.file_name(), {})

    def test_initialization_large(self, storage, faker):
        # type: (fs.FileSystemStorage, Faker) -> None
        storage.settings["max_size"] = 5
        with pytest.raises(exceptions.LargeUploadError):
            storage.initialize_multipart_upload(faker.file_name(), {"size": 10})

    def test_initialization(self, storage, faker):
        # type: (fs.FileSystemStorage, Faker) -> None
        content = b"hello world"
        data = storage.initialize_multipart_upload(
            faker.file_name(),
            {"size": len(content)},
        )
        assert data["size"] == len(content)
        assert data["uploaded"] == 0

    def test_update_invalid(self, storage, faker):
        # type: (fs.FileSystemStorage, Faker) -> None
        content = b"hello world"
        data = storage.initialize_multipart_upload(
            faker.file_name(),
            {"size": len(content)},
        )
        with pytest.raises(tk.ValidationError):
            storage.update_multipart_upload(data, {})

    def test_update(self, storage, faker):
        # type: (fs.FileSystemStorage, Faker) -> None
        content = b"hello world"
        data = storage.initialize_multipart_upload(
            faker.file_name(),
            {"size": len(content)},
        )

        data = storage.update_multipart_upload(
            data,
            {"upload": FileStorage(BytesIO(content[:5]))},
        )
        assert data["size"] == len(content)
        assert data["uploaded"] == 5

        data = storage.update_multipart_upload(
            data,
            {"upload": FileStorage(BytesIO(content[:5])), "position": 3},
        )
        assert data["size"] == len(content)
        assert data["uploaded"] == 8

        with pytest.raises(exceptions.UploadOutOfBoundError):
            storage.update_multipart_upload(
                data,
                {"upload": FileStorage(BytesIO(content))},
            )

        missing_size = data["size"] - data["uploaded"]
        data = storage.update_multipart_upload(
            data,
            {"upload": FileStorage(BytesIO(content[-missing_size:]))},
        )
        assert data["size"] == len(content)
        assert data["uploaded"] == len(content)

    def test_complete(self, storage, faker):
        # type: (fs.FileSystemStorage, Faker) -> None
        content = b"hello world"
        data = storage.initialize_multipart_upload(
            faker.file_name(),
            {"size": len(content)},
        )

        with pytest.raises(tk.ValidationError):
            storage.complete_multipart_upload(data, {})

        data = storage.update_multipart_upload(
            data,
            {"upload": FileStorage(BytesIO(content))},
        )
        data = storage.complete_multipart_upload(data, {})
        assert data["size"] == len(content)
        assert data["hash"] == hashlib.md5(content).hexdigest()

    def test_show(self, storage, faker):
        # type: (fs.FileSystemStorage, Faker) -> None
        content = b"hello world"

        data = storage.initialize_multipart_upload(
            faker.file_name(),
            {"size": len(content)},
        )
        assert storage.show_multipart_upload(data) == data

        data = storage.update_multipart_upload(
            data,
            {"upload": FileStorage(BytesIO(content))},
        )
        assert storage.show_multipart_upload(data) == data

        storage.complete_multipart_upload(data, {})
        assert storage.show_multipart_upload(data) == data


class TestManager:
    def test_removal(self, storage):
        # type: (fs.FileSystemStorage) -> None
        result = storage.upload("", FileStorage(), {})
        filepath = os.path.join(storage.settings["path"], result["filename"])
        assert os.path.exists(filepath)

        assert storage.remove(result)
        assert not os.path.exists(filepath)

    def test_removal_missing(self, storage):
        # type: (fs.FileSystemStorage) -> None
        result = storage.upload("", FileStorage(), {})
        assert storage.remove(result)
        assert not storage.remove(result)


class TestReader:
    def test_stream(self, storage, faker):
        # type: (fs.FileSystemStorage, Faker) -> None
        data = faker.binary(100)
        result = storage.upload("", FileStorage(BytesIO(data)), {})

        stream = storage.stream(result)

        assert stream.read() == data

    def test_content(self, storage, faker):
        # type: (fs.FileSystemStorage, Faker) -> None
        data = faker.binary(100)
        result = storage.upload("", FileStorage(BytesIO(data)), {})

        content = storage.content(result)

        assert content == data

    def test_missing(self, storage, faker):
        # type: (fs.FileSystemStorage, Faker) -> None
        result = storage.upload("", FileStorage(), {})
        result["filename"] += faker.uuid4()

        with pytest.raises(exceptions.MissingFileError):
            storage.stream(result)

        with pytest.raises(exceptions.MissingFileError):
            storage.content(result)


class TestStorage:
    def test_missing_path(self, tmp_path):
        # type: (str) -> None
        with pytest.raises(exceptions.InvalidStorageConfigurationError):
            fs.FileSystemStorage(path=os.path.join(str(tmp_path), "not-real"))

    def test_missing_path_created(self, tmp_path):
        # type: (str) -> None
        path = os.path.join(str(tmp_path), "not-real")
        assert not os.path.exists(path)

        fs.FileSystemStorage(path=path, create_path=True)
        assert os.path.exists(path)
