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
        assert result["url"].endswith(filename)


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
class TestFileDelete:
    def test_basic_show(self, random_file):
        result = call_action("files_file_show", id=random_file["id"])
        assert result == random_file

        result = call_action("files_file_show", id=random_file["name"])
        assert result == random_file
