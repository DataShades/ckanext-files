from __future__ import annotations

from typing import Any

import pytest

from ckanext.files import config

from _pytest.monkeypatch import MonkeyPatch  # isort: skip # noqa: F401


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
    def adapt_to_ckan_version(self, settings: dict[str, Any]) -> dict[str, Any]:
        """CKAN v2.10 has max_size added to default storage by config
        declaration.

        """

        settings.setdefault("max_size", 0)

        return settings

    def test_empty(self):
        """With no customization we have only storage defined by test.ini"""

        assert config.storages() == {
            "default": self.adapt_to_ckan_version(
                {
                    "type": "files:redis",
                    "prefix": "ckanext:files:test.ckan.net:file_content:",
                    "name": "default",
                },
            ),
        }

    def test_customized(self, monkeypatch: MonkeyPatch, ckan_config: dict[str, Any]):
        """Storage configuration grouped by the storage name."""
        patches: list[tuple[str, str]] = [
            ("default.type", "files:redis"),
            ("test.type", "test"),
            ("test.path", "somepath"),
            ("another.type", "fancy"),
            ("another.location_strategy", "hello"),
        ]
        for key, value in patches:
            monkeypatch.setitem(ckan_config, config.STORAGE_PREFIX + key, value)

        storages = config.storages()

        assert storages == {
            "default": self.adapt_to_ckan_version(
                {
                    "type": "files:redis",
                    "prefix": "ckanext:files:test.ckan.net:file_content:",
                    "name": "default",
                },
            ),
            "test": {"type": "test", "path": "somepath"},
            "another": {"type": "fancy", "location_strategy": "hello"},
        }

    @pytest.mark.ckan_config(config.STORAGE_PREFIX + "another", "test")
    def test_non_setting(self):
        """Only `<PREFIX>.<NAME>.<OPTION>` settings are grouped. If `.<OPTION>`
        part is missing, we ignore this line.

        """

        storages = config.storages()

        assert storages == {
            "default": self.adapt_to_ckan_version(
                {
                    "type": "files:redis",
                    "prefix": "ckanext:files:test.ckan.net:file_content:",
                    "name": "default",
                },
            ),
        }
