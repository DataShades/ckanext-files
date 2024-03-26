import pytest
from faker import Faker  # pytest: skip # noqa: F401
from werkzeug.datastructures import FileStorage

import ckan.plugins.toolkit as tk

from ckanext.files.logic import validators


class TestIntoUpload:
    def test_file_storage(self):
        """FileStorage instances returned as-is."""
        upload = FileStorage()

        assert validators.files_into_upload(upload) is upload

    def test_str(self, faker):
        # type: (Faker) -> None
        """Strings converted into FileStorage."""
        string = faker.pystr()
        upload = validators.files_into_upload(string)

        assert isinstance(upload, FileStorage)
        assert upload.stream.read() == string.encode()

    def test_bytes(self, faker):
        # type: (Faker) -> None
        """Bytes converted into FileStorage."""
        binary = faker.binary(100)
        upload = validators.files_into_upload(binary)

        assert isinstance(upload, FileStorage)
        assert upload.stream.read() == binary

    def test_wrong_type(self):
        """Any unexpected value causes an exception."""
        with pytest.raises(tk.Invalid):
            validators.files_into_upload(123)


class TestParseFilesize:
    def test_int(self, faker):
        # type: (Faker) -> None
        """Numbers are not changed by validator."""

        value = faker.pyint()
        assert validators.files_parse_filesize(value) is value

    def test_str(self):
        """Strings are converted into a number."""
        assert validators.files_parse_filesize("10K") == 10000

    def test_wrong_value(self):
        """Any unexpected value causes an exception."""
        with pytest.raises(tk.Invalid):
            validators.files_parse_filesize("10P")
