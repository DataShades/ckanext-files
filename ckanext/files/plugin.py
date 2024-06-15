from __future__ import annotations

import json
import os
from typing import Any

import ckan.plugins as p
import ckan.plugins.toolkit as tk
from ckan.config.declaration import Declaration, Key
from ckan.exceptions import CkanConfigurationException
from ckan.logic import clear_validators_cache

from . import base, config, exceptions, interfaces, storage, utils


@tk.blanket.helpers
@tk.blanket.validators
@tk.blanket.actions
@tk.blanket.auth_functions
@tk.blanket.cli
@tk.blanket.blueprints
class FilesPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurable)
    p.implements(p.IConfigurer, inherit=True)
    p.implements(interfaces.IFiles, inherit=True)

    p.implements(p.IConfigDeclaration)

    def declare_config_options(self, declaration: Declaration, key: Key):
        import yaml

        clear_validators_cache()

        here = os.path.dirname(__file__)
        with open(os.path.join(here, "config_declaration.yaml"), "rb") as src:
            declaration.load_dict(yaml.safe_load(src))

        _register_adapters()
        for name, settings in config.storages().items():
            storage_key = key.from_string(config.STORAGE_PREFIX + name)

            if tk.check_ckan_version("2.10.3"):
                # literal evaluation in validators was added in
                # v2.10.3. Without it we cannot validate dynamically storage
                # type
                available_adapters = json.dumps(
                    list(base.adapters),
                    separators=(",", ":"),
                )

                declaration.declare(
                    storage_key.type,
                    settings.get("type"),
                ).append_validators(
                    f"one_of({available_adapters})",
                ).set_description(
                    "Storage adapter used by the storage",
                )

            adapter = base.adapters.get(settings.get("type", ""))
            if not adapter:
                continue

            adapter.declare_config_options(
                declaration,
                storage_key,
            )

    # IFiles
    def files_get_storage_adapters(self) -> dict[str, type[base.Storage]]:
        adapters: dict[str, type[base.Storage]] = {
            "files:fs": storage.FsStorage,
            "files:public_fs": storage.PublicFsStorage,
            "files:ckan_resource_fs": storage.CkanResourceFsStorage,
            "files:redis": storage.RedisStorage,
            "files:filebin": storage.FilebinStorage,
        }

        if hasattr(storage, "GoogleCloudStorage"):
            adapters.update({"files:google_cloud_storage": storage.GoogleCloudStorage})

        return adapters

    # IConfigurable
    def configure(self, config_: Any):
        _initialize_storages()
        _register_owner_getters()

    # IConfigurer
    def update_config(self, config_: Any):
        tk.add_template_directory(config_, "templates")
        tk.add_resource("assets", "files")
        tk.add_public_directory(config_, "public")

        if config.override_resource_form():
            tk.add_template_directory(config_, "resource_form_templates")


def _register_adapters():
    """Register all storage types provided by extensions."""

    base.adapters.reset()
    for plugin in p.PluginImplementations(interfaces.IFiles):
        for name, adapter in plugin.files_get_storage_adapters().items():
            base.adapters.register(name, adapter)


def _initialize_storages():
    """Initialize all configured storages.

    Raise an exception if storage type is not registered.
    """

    base.storages.reset()
    for name, settings in config.storages().items():
        try:
            storage = base.make_storage(name, settings)
        except exceptions.UnknownAdapterError as err:
            raise CkanConfigurationException(str(err)) from err

        base.storages.register(name, storage)


def _register_owner_getters():
    for plugin in p.PluginImplementations(interfaces.IFiles):
        for name, getter in plugin.files_register_owner_getters().items():
            utils.owner_getters.register(name, getter)
