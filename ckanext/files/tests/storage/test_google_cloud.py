from __future__ import annotations

import base64
import hashlib
import json
import os
from io import BytesIO
from typing import Any
from urllib.parse import quote_plus
from uuid import UUID

import pytest
from faker import Faker

import ckan.plugins.toolkit as tk

from ckanext.files import exceptions, shared
from ckanext.files.storage import google_cloud as gc

TEST_BUCKET = "ld-bq-test"


@pytest.fixture()
def upload_progress() -> dict[str, Any]:
    return {"size": 0, "uploaded": 0, "content": b"", "name": ""}


@pytest.fixture()
def storage() -> gc.GoogleCloudStorage:
    credentials_file = os.path.join(
        os.path.dirname(__file__),
        "fake_creds.json",
    )

    return gc.GoogleCloudStorage(
        gc.GoogleCloudStorage.prepare_settings(
            {
                "name": "test",
                "path": "test",
                "bucket": TEST_BUCKET,
                "credentials_file": credentials_file,
            },
        ),
    )


@pytest.fixture()
def mocked_token(responses: Any):
    responses.add(
        "POST",
        "https://oauth2.googleapis.com/token",
        json={
            "access_token": "ya29.c.c0AY_VpZgccnsCOsCGNFxy",
            "expires_in": 3599,
            "token_type": "Bearer",
        },
    )


def encode(content: bytes) -> str:
    digest = hashlib.md5(content).digest()

    return base64.encodebytes(digest).decode().strip()


@pytest.fixture()
def mocked_session_url():
    return (
        "https://storage.googleapis.com"
        + f"/upload/storage/v1/b/{TEST_BUCKET}/o?"
        + "uploadType=resumable&upload_id=test"
    )


@pytest.fixture()
def mocked_multipart_start(
    responses: Any,
    mocked_session_url: Any,
    mocked_token: Any,
    upload_progress: dict[str, Any],
):
    def post_callback(request: Any):
        upload_progress["size"] = int(request.headers.get("x-upload-content-length", 0))
        upload_progress["name"] = json.loads(request.body)["name"]
        return (200, {"location": mocked_session_url}, "")

    responses.add_callback(
        "POST",
        f"https://storage.googleapis.com/upload/storage/v1/b/{TEST_BUCKET}/o?uploadType=resumable",
        callback=post_callback,
    )


@pytest.fixture()
def mocked_multipart_update(
    responses: Any,
    mocked_session_url: Any,
    upload_progress: dict[str, Any],
):
    def put_callback(request: Any) -> Any:
        content_range = request.headers.get("content-range")
        headers = {}
        if content_range:
            range, total = content_range.split()[-1].split("/")
            if range == "*":
                if upload_progress["uploaded"] == upload_progress["size"]:
                    status = 200
                else:
                    status = 308
                    if upload_progress["uploaded"]:
                        headers["range"] = "bytes=0-{}".format(
                            upload_progress["uploaded"],
                        )
            else:
                total = int(total)
                start, end = map(int, range.split("-"))
                upload_progress["uploaded"] = end + 1
                upload_progress["content"] = (
                    upload_progress["content"][:start] + request.body
                )
                if end + 1 < total:
                    status = 308
                    headers["range"] = f"bytes=0-{end}"
                else:
                    status = 200

        else:
            status = 200

        return (
            status,
            headers,
            (
                ""
                if status == 308
                else json.dumps(
                    {
                        "size": str(upload_progress["uploaded"]),
                        "md5Hash": encode(upload_progress["content"]),
                        "contentType": "application/octet-stream",
                        "name": upload_progress["name"],
                    },
                )
            ),
        )

    responses.add_callback(
        "PUT",
        mocked_session_url,
        callback=put_callback,
    )


@pytest.fixture()
def mocked_upload(mocked_multipart_start: Any, mocked_multipart_update: Any):
    pass


class TestUploader:
    @pytest.mark.usefixtures("mocked_token", "mocked_upload")
    def test_result(self, storage: gc.GoogleCloudStorage, faker: Faker):
        content = faker.binary(100)
        result = storage.upload("", shared.make_upload(BytesIO(content)))

        assert UUID(result.location)
        assert result.size == len(content)
        assert result.hash == gc.decode(encode(content))


@pytest.mark.usefixtures("with_plugins")
class TestMultipartUploader:
    def test_initialization_large(self, storage: gc.GoogleCloudStorage, faker: Faker):
        storage.settings["max_size"] = 5
        with pytest.raises(exceptions.LargeUploadError):
            storage.multipart_start(faker.file_name(), shared.MultipartData(size=10))

    @pytest.mark.usefixtures("mocked_multipart_start")
    def test_initialization(self, storage: gc.GoogleCloudStorage, faker: Faker):
        content = b"hello world"
        data = storage.multipart_start(
            faker.file_name(),
            shared.MultipartData(size=len(content)),
        )
        assert data.size == len(content)
        assert data.storage_data["uploaded"] == 0
        assert data.storage_data["session_url"]

    @pytest.mark.usefixtures("mocked_multipart_start")
    def test_update_invalid(self, storage: gc.GoogleCloudStorage, faker: Faker):
        content = b"hello world"
        data = storage.multipart_start(
            faker.file_name(),
            shared.MultipartData(size=len(content)),
        )
        with pytest.raises(tk.ValidationError):
            storage.multipart_update(data)

    @pytest.mark.usefixtures("mocked_upload")
    def test_update(self, storage: gc.GoogleCloudStorage, faker: Faker):
        content = faker.binary(256 * 1024 * 2)
        data = storage.multipart_start(
            faker.file_name(),
            shared.MultipartData(size=len(content)),
        )

        with pytest.raises(tk.ValidationError):
            storage.multipart_update(
                data,
                upload=shared.make_upload(BytesIO(content[:5])),
            )

        data = storage.multipart_update(
            data,
            upload=shared.make_upload(BytesIO(content[: 256 * 1024])),
        )

        assert data.size == len(content)
        assert data.storage_data["uploaded"] == 256 * 1024

        with pytest.raises(exceptions.UploadOutOfBoundError):
            storage.multipart_update(data, upload=shared.make_upload(BytesIO(content)))

        missing_size = data.size - data.storage_data["uploaded"]
        data = storage.multipart_update(
            data,
            upload=shared.make_upload(BytesIO(content[-missing_size:])),
        )
        assert data.size == len(content)
        assert data.storage_data["uploaded"] == len(content)

    @pytest.mark.usefixtures("mocked_upload")
    def test_complete(self, storage: gc.GoogleCloudStorage, faker: Faker):
        content = b"hello world"
        data = storage.multipart_start(
            faker.file_name(),
            shared.MultipartData(
                content_type="application/octet-stream",
                size=len(content),
            ),
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

    @pytest.mark.usefixtures("mocked_upload")
    def test_show(self, storage: gc.GoogleCloudStorage, faker: Faker):
        content = b"hello world"

        data = storage.multipart_start(
            faker.file_name(),
            shared.MultipartData(
                content_type="application/octet-stream",
                size=len(content),
            ),
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
    @pytest.mark.usefixtures("mocked_upload")
    def test_removal(self, storage: gc.GoogleCloudStorage, responses: Any):
        result = storage.upload("", shared.make_upload(b""))
        name = os.path.join(storage.settings["path"], result.location)

        object_url = f"https://storage.googleapis.com/storage/v1/b/ld-bq-test/o/{quote_plus(name)}"
        responses.add("GET", object_url, status=200)
        responses.add("DELETE", object_url, status=200)

        assert storage.remove(result)

    @pytest.mark.usefixtures("mocked_upload")
    def test_removal_missing(self, storage: gc.GoogleCloudStorage, responses: Any):
        result = storage.upload("", shared.make_upload(b""))
        name = os.path.join(storage.settings["path"], result.location)

        object_url = f"https://storage.googleapis.com/storage/v1/b/ld-bq-test/o/{quote_plus(name)}"
        responses.add("GET", object_url, status=200)
        responses.add("GET", object_url, status=404)

        responses.add("DELETE", object_url, status=200)

        assert storage.remove(result)
        assert not storage.remove(result)


class TestStorage:
    def test_missing_path(self, tmp_path: Any):
        with pytest.raises(exceptions.InvalidStorageConfigurationError):
            gc.GoogleCloudStorage(
                gc.GoogleCloudStorage(
                    {"bucket": TEST_BUCKET, "credentials_file": "/not-real"},
                ),
            )
