import os

import pytest

from ckan.tests import factories
from ckan.tests.helpers import call_action

from ckanext.files.base import get_storage
from ckanext.files.exceptions import UnknownStorageError


@pytest.fixture()
def with_files_uploader(monkeypatch, tmpdir, ckan_config):
    monkeypatch.setitem(
        ckan_config,
        "ckanext.files.storage.resource.type",
        "files_uploader:resource",
    )
    monkeypatch.setitem(ckan_config, "ckanext.files.storage.resource.path", str(tmpdir))
    monkeypatch.setitem(
        ckan_config,
        "ckanext.files.storage.image.type",
        "files_uploader:image",
    )
    monkeypatch.setitem(ckan_config, "ckanext.files.storage.image.path", str(tmpdir))


class SharedTests:
    @pytest.mark.ckan_config("ckan.upload.group.mimetypes", "application/octet-stream")
    @pytest.mark.ckan_config("ckan.upload.group.types", "application")
    def test_group_upload(self, tmpdir, create_with_upload, faker):
        user = factories.User()
        group = create_with_upload(
            faker.binary(10),
            "image.png",
            context={"user": user["name"]},
            upload_field_name="image_upload",
            image_url="image.png",
            action="group_create",
            name=faker.word(),
        )
        filepath = os.path.join(
            tmpdir,
            "storage",
            "uploads",
            "group",
            group["image_url"],
        )
        assert os.path.exists(filepath)

    def test_resource_upload_goes_to_fs(self, tmpdir, create_with_upload):
        content = "hello world"
        package = factories.Dataset()
        resource = create_with_upload(content, "file.txt", package_id=package["id"])

        filepath = os.path.join(
            tmpdir,
            "resources",
            resource["id"][:3],
            resource["id"][3:6],
            resource["id"][6:],
        )
        assert os.path.exists(filepath)

        with open(filepath, "r") as src:
            assert src.read() == content

    def test_resource_download(self, app, create_with_upload):
        content = "hello world"
        package = factories.Dataset()
        resource = create_with_upload(content, "file.txt", package_id=package["id"])

        resp = app.get(
            "/dataset/{package_id}/resource/{id}/download".format(**resource),
        )
        assert resp.body == content

    def test_resource_deletion(self, create_with_upload, faker, tmpdir):
        """Files are kept in system when resource is deleted but removed when
        `clear_upload` field added to resource."""

        package = factories.Dataset()
        resource = create_with_upload(
            faker.binary(10),
            "file.txt",
            package_id=package["id"],
        )
        filepath = os.path.join(
            tmpdir,
            "resources",
            resource["id"][:3],
            resource["id"][3:6],
            resource["id"][6:],
        )
        assert os.path.exists(filepath)

        call_action("resource_patch", id=resource["id"], clear_upload=True)
        assert not os.path.exists(filepath)


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestNativeUploader(SharedTests):
    def test_resource_storage_is_not_registered(self):
        with pytest.raises(UnknownStorageError):
            get_storage("resource")


@pytest.mark.usefixtures("with_files_uploader", "with_plugins", "clean_db")
@pytest.mark.ckan_config("ckan.plugins", "files files_uploader")
class TestFilesUploader(SharedTests):
    def test_resource_storage_is_registered(self):
        assert get_storage("resource")
