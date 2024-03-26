import base64
import hashlib
import json
import os
from io import BytesIO
from uuid import UUID

import pytest
import six
from six.moves.urllib.parse import quote_plus
from werkzeug.datastructures import FileStorage

import ckan.plugins.toolkit as tk

from ckanext.files import exceptions
from ckanext.files.storage import google_cloud as gc

from faker import Faker  # isort: skip # noqa: F401
from ckanext.files import types  # isort: skip # noqa: F401

TEST_BUCKET = "ld-bq-test"


@pytest.fixture()
def upload_progress():
    return {"size": 0, "uploaded": 0, "content": b"", "name": ""}


@pytest.fixture()
def storage():
    # type: () -> gc.GoogleCloudStorage
    return gc.GoogleCloudStorage(name="test", path="test", bucket=TEST_BUCKET)


@pytest.fixture()
def mocked_token(responses):
    responses.add(
        "POST",
        "https://oauth2.googleapis.com/token",
        json={
            "access_token": "ya29.c.c0AY_VpZgccnsCOsCGNFxy",
            "expires_in": 3599,
            "token_type": "Bearer",
        },
    )


def encode(content):
    # type: (bytes) -> str
    digest = hashlib.md5(content).digest()

    if six.PY3:
        return base64.encodebytes(digest).decode().strip()

    return base64.encodestring(digest).strip()


@pytest.fixture()
def mocked_session_url():
    return (
        "https://storage.googleapis.com"
        + "/upload/storage/v1/b/{}/o?".format(TEST_BUCKET)
        + "uploadType=resumable&upload_id=test"
    )


@pytest.fixture()
def mocked_upload_initialize(
    responses,
    mocked_session_url,
    mocked_token,
    upload_progress,
):
    # type: (types.Any, types.Any, types.Any, dict[str, types.Any]) -> None
    def post_callback(request):
        upload_progress["size"] = int(request.headers.get("x-upload-content-length", 0))
        upload_progress["name"] = json.loads(request.body)["name"]
        return (200, {"location": mocked_session_url}, "")

    responses.add_callback(
        "POST",
        "https://storage.googleapis.com/upload/storage/v1/b/{}/o?uploadType=resumable".format(
            TEST_BUCKET,
        ),
        callback=post_callback,
    )


@pytest.fixture()
def mocked_upload_update(responses, mocked_session_url, upload_progress):
    # type: (types.Any, types.Any, dict[str, types.Any]) -> None

    def put_callback(request):
        # type: (types.Any) -> types.Any

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
                    headers["range"] = "bytes=0-{}".format(end)
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
def mocked_upload(mocked_upload_initialize, mocked_upload_update):
    # type: (types.Any, types.Any) -> None
    pass


class TestUploader:
    @pytest.mark.usefixtures("mocked_token", "mocked_upload")
    def test_result(self, storage, faker):
        # type: (gc.GoogleCloudStorage, Faker) -> None
        content = faker.binary(100)
        result = storage.upload("", FileStorage(BytesIO(content)), {})

        assert UUID(result["filename"])
        assert result["size"] == len(content)
        assert result["hash"] == gc.decode(encode(content))


@pytest.mark.usefixtures("with_plugins")
class TestMultipartUploader:
    def test_initialization_invalid(self, storage, faker):
        # type: (gc.GoogleCloudStorage, Faker) -> None
        with pytest.raises(tk.ValidationError):
            storage.initialize_multipart_upload(faker.file_name(), {})

    def test_initialization_large(self, storage, faker):
        # type: (gc.GoogleCloudStorage, Faker) -> None
        storage.settings["max_size"] = 5
        with pytest.raises(exceptions.LargeUploadError):
            storage.initialize_multipart_upload(faker.file_name(), {"size": 10})

    @pytest.mark.usefixtures("mocked_upload_initialize")
    def test_initialization(self, storage, faker):
        # type: (gc.GoogleCloudStorage, Faker) -> None
        content = b"hello world"
        data = storage.initialize_multipart_upload(
            faker.file_name(),
            {"size": len(content)},
        )
        assert data["size"] == len(content)
        assert data["uploaded"] == 0
        assert data["session_url"]

    @pytest.mark.usefixtures("mocked_upload_initialize")
    def test_update_invalid(self, storage, faker):
        # type: (gc.GoogleCloudStorage, Faker) -> None
        content = b"hello world"
        data = storage.initialize_multipart_upload(
            faker.file_name(),
            {"size": len(content)},
        )
        with pytest.raises(tk.ValidationError):
            storage.update_multipart_upload(data, {})

    @pytest.mark.usefixtures("mocked_upload")
    def test_update(self, storage, faker):
        # type: (gc.GoogleCloudStorage, Faker) -> None
        content = faker.binary(256 * 1024 * 2)
        data = storage.initialize_multipart_upload(
            faker.file_name(),
            {"size": len(content)},
        )

        with pytest.raises(tk.ValidationError):
            storage.update_multipart_upload(
                data,
                {"upload": FileStorage(BytesIO(content[:5]))},
            )

        data = storage.update_multipart_upload(
            data,
            {"upload": FileStorage(BytesIO(content[: 256 * 1024]))},
        )

        assert data["size"] == len(content)
        assert data["uploaded"] == 256 * 1024

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

    @pytest.mark.usefixtures("mocked_upload")
    def test_complete(self, storage, faker):
        # type: (gc.GoogleCloudStorage, Faker) -> None
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

    @pytest.mark.usefixtures("mocked_upload")
    def test_show(self, storage, faker):
        # type: (gc.GoogleCloudStorage, Faker) -> None
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
    @pytest.mark.usefixtures("mocked_upload")
    def test_removal(self, storage, responses):
        # type: (gc.GoogleCloudStorage, types.Any) -> None
        result = storage.upload("", FileStorage(), {})
        name = os.path.join(storage.settings["path"], result["filename"])

        object_url = (
            "https://storage.googleapis.com/storage/v1/b/ld-bq-test/o/{}".format(
                quote_plus(name),
            )
        )
        responses.add("GET", object_url, status=200)
        responses.add("DELETE", object_url, status=200)

        assert storage.remove(result)

    @pytest.mark.usefixtures("mocked_upload")
    def test_removal_missing(self, storage, responses):
        # type: (gc.GoogleCloudStorage, types.Any) -> None
        result = storage.upload("", FileStorage(), {})
        name = os.path.join(storage.settings["path"], result["filename"])

        object_url = (
            "https://storage.googleapis.com/storage/v1/b/ld-bq-test/o/{}".format(
                quote_plus(name),
            )
        )
        responses.add("GET", object_url, status=200)
        responses.add("GET", object_url, status=404)

        responses.add("DELETE", object_url, status=200)

        assert storage.remove(result)
        assert not storage.remove(result)


class TestStorage:
    def test_missing_path(self, tmp_path):
        # type: (str) -> None
        with pytest.raises(exceptions.InvalidStorageConfigurationError):
            gc.GoogleCloudStorage(bucket=TEST_BUCKET, credentials_file="/not-real")
