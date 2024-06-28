import hashlib
import os
from io import BytesIO
from pathlib import Path
from uuid import UUID

import pytest
from faker import Faker

import ckan.plugins.toolkit as tk

from ckanext.files import exceptions, shared
from ckanext.files.storage import fs


@pytest.fixture()
def storage(tmp_path: Path):
    return fs.FsStorage(
        fs.FsStorage.prepare_settings({"name": "test", "path": str(tmp_path)}),
    )


class TestUploader:
    def test_key(self, storage: fs.FsStorage):
        result = storage.upload("", shared.make_upload(b""))

        assert UUID(result.location)
        assert result.size == 0

        filepath = os.path.join(storage.settings["path"], result.location)

        assert os.path.exists(filepath)
        assert os.path.getsize(filepath) == 0

    def test_content(self, storage: fs.FsStorage, faker: Faker):
        content = faker.binary(100)
        result = storage.upload("", shared.make_upload(BytesIO(content)))

        assert result.size == 100

        filepath = os.path.join(storage.settings["path"], result.location)
        with open(filepath, "rb") as src:
            assert src.read() == content

    def test_hash(self, storage: fs.FsStorage, faker: Faker):
        result = storage.upload("", shared.make_upload(b""))
        assert result.hash == hashlib.md5().hexdigest()

        content = faker.binary(100)
        result = storage.upload("", shared.make_upload(BytesIO(content)))
        assert result.hash == hashlib.md5(content).hexdigest()


@pytest.mark.usefixtures("with_plugins")
class TestMultipartUploader:
    def test_initialization_large(self, storage: fs.FsStorage, faker: Faker):
        storage.settings["max_size"] = 5
        with pytest.raises(exceptions.LargeUploadError):
            storage.multipart_start(faker.file_name(), shared.MultipartData(size=10))

    def test_initialization(self, storage: fs.FsStorage, faker: Faker):
        content = b"hello world"
        data = storage.multipart_start(
            faker.file_name(),
            shared.MultipartData(size=len(content)),
        )
        assert data.size == len(content)
        assert data.storage_data["uploaded"] == 0

    def test_update_invalid(self, storage: fs.FsStorage, faker: Faker):
        content = b"hello world"
        data = storage.multipart_start(
            faker.file_name(),
            shared.MultipartData(size=len(content)),
        )
        with pytest.raises(tk.ValidationError):
            storage.multipart_update(data)

    def test_update(self, storage: fs.FsStorage, faker: Faker):
        content = b"hello world"
        data = storage.multipart_start(
            faker.file_name(),
            shared.MultipartData(size=len(content)),
        )

        data = storage.multipart_update(
            data,
            upload=shared.make_upload(BytesIO(content[:5])),
        )
        assert data.size == len(content)
        assert data.storage_data["uploaded"] == 5

        data = storage.multipart_update(
            data,
            upload=shared.make_upload(BytesIO(content[:5])),
            position=3,
        )
        assert data.size == len(content)
        assert data.storage_data["uploaded"] == 8

        with pytest.raises(exceptions.UploadOutOfBoundError):
            storage.multipart_update(data, upload=shared.make_upload(BytesIO(content)))

        missing_size = data.size - data.storage_data["uploaded"]
        data = storage.multipart_update(
            data,
            upload=shared.make_upload(BytesIO(content[-missing_size:])),
        )
        assert data.size == len(content)
        assert data.storage_data["uploaded"] == len(content)

    def test_complete(self, storage: fs.FsStorage, faker: Faker):
        content = b"hello world"
        data = storage.multipart_start(
            faker.file_name(),
            shared.MultipartData(content_type="text/plain", size=len(content)),
        )

        with pytest.raises(exceptions.UploadSizeMismatchError):
            storage.multipart_complete(data)

        data = storage.multipart_update(
            data,
            upload=shared.make_upload(BytesIO(content)),
        )
        data = storage.multipart_complete(data)
        assert data.size == len(content)
        assert data.hash == hashlib.md5(content).hexdigest()

    def test_show(self, storage: fs.FsStorage, faker: Faker):
        content = b"hello world"

        data = storage.multipart_start(
            faker.file_name(),
            shared.MultipartData(content_type="text/plain", size=len(content)),
        )
        assert storage.multipart_refresh(data) == data

        data = storage.multipart_update(
            data,
            upload=shared.make_upload(BytesIO(content)),
        )
        assert storage.multipart_refresh(data) == data

        storage.multipart_complete(data)
        assert storage.multipart_refresh(data) == data


class TestManager:
    def test_removal(self, storage: fs.FsStorage):
        result = storage.upload("", shared.make_upload(b""))
        filepath = os.path.join(storage.settings["path"], result.location)
        assert os.path.exists(filepath)

        assert storage.remove(result)
        assert not os.path.exists(filepath)

    def test_removal_missing(self, storage: fs.FsStorage):
        result = storage.upload("", shared.make_upload(b""))
        assert storage.remove(result)
        assert not storage.remove(result)


class TestReader:
    def test_stream(self, storage: fs.FsStorage, faker: Faker):
        data = faker.binary(100)
        result = storage.upload("", shared.make_upload(BytesIO(data)))

        stream = storage.stream(result)

        assert b"".join(stream) == data

    def test_content(self, storage: fs.FsStorage, faker: Faker):
        data = faker.binary(100)
        result = storage.upload("", shared.make_upload(BytesIO(data)))

        content = storage.content(result)

        assert content == data

    def test_missing(self, storage: fs.FsStorage, faker: Faker):
        result = storage.upload("", shared.make_upload(b""))
        result.location += str(faker.uuid4())

        with pytest.raises(exceptions.MissingFileError):
            storage.stream(result)

        with pytest.raises(exceptions.MissingFileError):
            storage.content(result)


class TestStorage:
    def test_missing_path(self, tmp_path: Path):
        with pytest.raises(exceptions.InvalidStorageConfigurationError):
            fs.FsStorage(
                fs.FsStorage.prepare_settings(
                    {"path": os.path.join(str(tmp_path), "not-real")},
                ),
            )

    def test_missing_path_created(self, tmp_path: Path):
        path = os.path.join(str(tmp_path), "not-real")
        assert not os.path.exists(path)

        fs.FsStorage(fs.FsStorage.prepare_settings({"path": path, "create_path": True}))
        assert os.path.exists(path)
