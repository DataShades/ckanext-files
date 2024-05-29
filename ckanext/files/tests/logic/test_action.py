from __future__ import annotations

from typing import Any

import pytest

import ckan.model as model
from ckan.tests.helpers import call_action

from ckanext.files.model import File


@pytest.fixture
def random_file(create_with_upload: Any, faker: Any):
    return create_with_upload(
        faker.binary(10),
        faker.file_name(),
        action="files_file_create",
        name=faker.name(),
    )


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestFileCreate:
    def test_basic_file(self, create_with_upload: Any):
        filename = "file.txt"
        result = create_with_upload(
            "hello",
            filename,
            action="files_file_create",
            name="Test file.txt",
        )

        assert result["name"] == "Test_file.txt"


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestFileDelete:
    def test_basic_delete(self, random_file: dict[str, Any]):
        q = model.Session.query(File)
        assert q.count() == 1
        call_action("files_file_delete", id=random_file["id"])
        assert not q.count()


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestFileShow:
    def test_basic_show(self, random_file: dict[str, Any]):
        result = call_action("files_file_show", id=random_file["id"])
        assert result["id"] == random_file["id"]

        result = call_action("files_file_show", id=random_file["id"])
        assert result["id"] == random_file["id"]
