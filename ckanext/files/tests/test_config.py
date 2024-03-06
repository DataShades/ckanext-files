import pytest

from ckanext.files import config


class TestDefault:
    def test_default_value(self):
        """Verify that default value does not change accidentally.

        If you are modifying this test, don't forget to add changelog entry!

        """
        assert config.default_storage() == "default"

    @pytest.mark.ckan_config(config.DEFAULT_STORAGE, "test")
    def test_customized(self):
        """Default storage can be changed."""
        assert config.default_storage() == "test"


class TestStorages:
    def test_empty(self):
        """With no customization we have only storage defined by test.ini"""

        assert config.storages() == {"default": {"type": "files:redis"}}

    def test_customized(self, monkeypatch, ckan_config):
        """Storage configuration grouped by the storage name."""
        patches = [
            ("default.type", "files:redis"),
            ("test.type", "test"),
            ("test.path", "somepath"),
            ("another.type", "fancy"),
            ("another.name_strategy", "hello"),
        ]  # type: list[tuple[str, str]]
        for key, value in patches:
            monkeypatch.setitem(ckan_config, config.STORAGE_PREFIX + key, value)

        storages = config.storages()

        assert storages == {
            "default": {"type": "files:redis"},
            "test": {"type": "test", "path": "somepath"},
            "another": {"type": "fancy", "name_strategy": "hello"},
        }

    @pytest.mark.ckan_config(config.STORAGE_PREFIX + "another", "test")
    def test_non_setting(self):
        """Only `<PREFIX>.<NAME>.<OPTION>` settings are grouped. If `.<OPTION>`
        part is missing, we ignore this line.

        """

        storages = config.storages()

        assert storages == {"default": {"type": "files:redis"}}
