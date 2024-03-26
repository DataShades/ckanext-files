import pytest

import ckan.model as model
from ckan.tests.helpers import call_action

from ckanext.files.model import File

from ckanext.files import types  # isort: skip # noqa: F401


@pytest.fixture
def random_file(create_with_upload, faker):
    return create_with_upload(
        faker.binary(10),
        faker.file_name(),
        action="files_file_create",
        name=faker.name(),
    )


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestFileCreate:
    def test_basic_file(self, create_with_upload):
        filename = "file.txt"
        result = create_with_upload(
            "hello",
            filename,
            action="files_file_create",
            name="Test file.txt",
        )

        assert result["name"] == "Test file.txt"


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestFileDelete:
    def test_basic_delete(self, random_file):
        # type: (dict[str, types.Any]) -> None
        q = model.Session.query(File)
        assert q.count() == 1
        call_action("files_file_delete", id=random_file["id"])
        assert not q.count()


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestFileShow:
    def test_basic_show(self, random_file):
        # type: (dict[str, types.Any]) -> None
        result = call_action("files_file_show", id=random_file["id"])
        assert result["id"] == random_file["id"]

        result = call_action("files_file_show", id=random_file["id"])
        assert result["id"] == random_file["id"]
