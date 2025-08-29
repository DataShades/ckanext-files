from __future__ import annotations

from typing import Any

import pytest
from _pytest.monkeypatch import MonkeyPatch

from ckanext.files import config


class TestDefault:
    def test_default_value(self):
        """Verify that default value does not change accidentally.

        If you are modifying this test, don't forget to add changelog entry!

        """
        assert config.default_storage() == "test"

    @pytest.mark.ckan_config(config.DEFAULT_STORAGE, "test")
    def test_customized(self):
        """Default storage can be changed."""
        assert config.default_storage() == "test"


class TestStorages:
    def test_empty(self, ckan_config: dict[str, Any]):
        """With no customization we have only storage defined by test.ini."""
        assert config.storages() == {
            "test": {
                "type": "files:redis",
                "bucket": "ckanext:files:test.ckan.net:file_content",
                "url": ckan_config["ckan.redis.url"],
                "override_existing": False,
                "name": "test",
                "supported_types": [],
                "disabled_capabilities": [],
                "location_transformers": [],
                "max_size": 0,
                "initialize": False,
                "path": "",
            },
        }

    def test_customized(self, monkeypatch: MonkeyPatch, ckan_config: dict[str, Any]):
        """Storage configuration grouped by the storage name."""
        patches: list[tuple[str, Any]] = [
            ("test.type", "files:redis"),
            ("hehe.type", "hehe"),
            ("hehe.path", "somepath"),
            ("another.type", "fancy"),
            ("another.location_transformers", ["hello"]),
        ]
        for key, value in patches:
            monkeypatch.setitem(ckan_config, config.STORAGE_PREFIX + key, value)

        storages = config.storages()

        assert storages == {
            "test": {
                "type": "files:redis",
                "bucket": "ckanext:files:test.ckan.net:file_content",
                "url": ckan_config["ckan.redis.url"],
                "override_existing": False,
                "name": "test",
                "supported_types": [],
                "initialize": False,
                "path": "",
                "disabled_capabilities": [],
                "location_transformers": [],
                "max_size": 0,
            },
            "hehe": {
                "type": "hehe",
                "path": "somepath",
            },
            "another": {
                "type": "fancy",
                "location_transformers": ["hello"],
            },
        }

    @pytest.mark.ckan_config(config.STORAGE_PREFIX + "another", "test")
    def test_non_setting(self, ckan_config: dict[str, Any]):
        """Test extra items from settings.

        Only `<PREFIX>.<NAME>.<OPTION>` settings are grouped. If `.<OPTION>`
        part is missing, we ignore this line.
        """
        storages = config.storages()

        assert storages == {
            "test": {
                "type": "files:redis",
                "bucket": "ckanext:files:test.ckan.net:file_content",
                "url": ckan_config["ckan.redis.url"],
                "override_existing": False,
                "name": "test",
                "initialize": False,
                "path": "",
                "supported_types": [],
                "disabled_capabilities": [],
                "location_transformers": [],
                "max_size": 0,
            },
        }
