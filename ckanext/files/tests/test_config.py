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
        assert config.default_storage() == "default"

    @pytest.mark.ckan_config(config.DEFAULT_STORAGE, "test")
    def test_customized(self):
        """Default storage can be changed."""
        assert config.default_storage() == "test"


class TestStorages:
    def test_empty(self, ckan_config: dict[str, Any]):
        """With no customization we have only storage defined by test.ini."""
        assert config.storages() == {
            "default": {
                "type": "files:redis",
                "path": "ckanext:files:test.ckan.net:file_content",
                "redis_url": ckan_config["ckan.redis.url"],
                "override_existing": False,
                "name": "default",
                "supported_types": [],
                "location_transformers": [],
                "max_size": 0,
            },
        }

    def test_customized(self, monkeypatch: MonkeyPatch, ckan_config: dict[str, Any]):
        """Storage configuration grouped by the storage name."""
        patches: list[tuple[str, Any]] = [
            ("default.type", "files:redis"),
            ("test.type", "test"),
            ("test.path", "somepath"),
            ("another.type", "fancy"),
            ("another.location_transformers", ["hello"]),
        ]
        for key, value in patches:
            monkeypatch.setitem(ckan_config, config.STORAGE_PREFIX + key, value)

        storages = config.storages()

        assert storages == {
            "default": {
                "type": "files:redis",
                "path": "ckanext:files:test.ckan.net:file_content",
                "redis_url": ckan_config["ckan.redis.url"],
                "override_existing": False,
                "name": "default",
                "supported_types": [],
                "location_transformers": [],
                "max_size": 0,
            },
            "test": {
                "type": "test",
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
            "default": {
                "type": "files:redis",
                "path": "ckanext:files:test.ckan.net:file_content",
                "redis_url": ckan_config["ckan.redis.url"],
                "override_existing": False,
                "name": "default",
                "supported_types": [],
                "location_transformers": [],
                "max_size": 0,
            },
        }
