import pytest

import ckan.model as model
from ckan.tests.helpers import call_action

from ckanext.files.model import File


@pytest.fixture
def random_file(create_with_upload, faker):
    return create_with_upload(
        faker.binary(10),
        faker.file_name(),
        action="files_file_create",
        name=faker.unique.name(),
    )


@pytest.mark.usefixtures("with_plugins")
class TestFileCreate:
    def test_basic_file(self, create_with_upload):
        filename = "file.txt"
        result = create_with_upload(
            "hello",
            filename,
            action="files_file_create",
            name="test file",
        )

        assert result["name"] == "test file"
        assert result["url"] == f"/files/get_url/{result['id']}"


@pytest.mark.usefixtures("with_plugins")
class TestFileUpdate:
    def test_basic_update(self, random_file):
        result = call_action(
            "files_file_update", name="another name", id=random_file["id"]
        )
        assert result["id"] == random_file["id"]
        assert result["name"] == "another name"


@pytest.mark.usefixtures("with_plugins")
class TestFileDelete:
    def test_basic_delete(self, random_file):
        q = model.Session.query(File)
        assert q.count() == 1
        call_action("files_file_delete", id=random_file["id"])
        assert not q.count()


@pytest.mark.usefixtures("with_plugins")
class TestFileShow:
    def test_basic_show(self, random_file):
        result = call_action("files_file_show", id=random_file["id"])
        assert result["id"] == random_file["id"]

        result = call_action("files_file_show", id=random_file["name"])
        assert result["id"] == random_file["id"]

    def test_show_updates_last_access(self, random_file):
        result = call_action("files_file_show", id=random_file["id"])
        assert result["last_access"] != random_file["last_access"]


@pytest.mark.usefixtures("with_plugins")
class TestGetUnusedFiles:
    def test_no_unused_files(self, random_file):
        assert not call_action("files_get_unused_files")

    @pytest.mark.ckan_config("ckanext.files.unused_threshold", 0)
    def test_configure_default_threshold(self, random_file, ckan_config):
        assert call_action("files_get_unused_files")
