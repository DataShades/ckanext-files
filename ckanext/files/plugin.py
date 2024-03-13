import json
import os

import ckan.plugins as p
import ckan.plugins.toolkit as tk
from ckan.exceptions import CkanConfigurationException

from ckanext.files import (
    base,
    cli,
    config,
    exceptions,
    helpers,
    interfaces,
    storage,
    views,
)
from ckanext.files.logic import action, auth, validators

from ckanext.files import types  # isort: skip # noqa: F401


class FilesPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurable)
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)
    p.implements(p.IValidators)
    p.implements(p.IBlueprint)
    p.implements(p.ITemplateHelpers)
    p.implements(interfaces.IFiles)

    if tk.check_ckan_version("2.9"):
        p.implements(p.IClick)

    if tk.check_ckan_version("2.10"):
        p.implements(p.IConfigDeclaration)

        def declare_config_options(self, declaration, key):
            # type: (types.Declaration, types.Key) -> None
            import yaml

            here = os.path.dirname(__file__)
            with open(os.path.join(here, "config_declaration.yaml"), "rb") as src:
                declaration.load_dict(yaml.safe_load(src))

            _register_adapters()
            for name, settings in config.storages().items():
                storage_key = key.from_string(config.STORAGE_PREFIX + name)

                if tk.check_ckan_version("2.10.3"):
                    available_adapters = json.dumps(
                        list(base.adapters),
                        separators=(",", ":"),
                    )

                    declaration.declare(
                        storage_key.type,
                        settings.get("type"),
                    ).append_validators(
                        "one_of({})".format(available_adapters),
                    ).set_description(
                        "Storage adapter used by the storage",
                    )

                adapter = base.adapters.get(settings.get("type"))
                if not adapter:
                    continue

                adapter.declare_config_options(
                    declaration,
                    storage_key,
                )

    # IFiles
    def files_get_storage_adapters(self):
        # type: () -> dict[str, types.Any]
        adapters = {}  # type: dict[str, types.Any]
        adapters = {
            "files:fs": storage.FileSystemStorage,
            "files:public_fs": storage.PublicFileSystemStorage,
            "files:redis": storage.RedisStorage,
        }

        if hasattr(storage, "GoogleCloudStorage"):
            adapters.update({"files:google_cloud_storage": storage.GoogleCloudStorage})

        return adapters

    # IConfigurable
    def configure(self, config_):
        # type: (types.Any) -> None

        # starting from CKAN v2.10, adapters are registered alongside with
        # config declaration, to enrich declarations with adapter-specific
        # options.
        if not tk.check_ckan_version("2.10"):
            _register_adapters()

        _initialize_storages()

    # IConfigurer
    def update_config(self, config_):
        # type: (types.Any) -> None
        tk.add_template_directory(config_, "templates")
        tk.add_resource("assets", "files")
        tk.add_public_directory(config_, "public")

    # IActions
    def get_actions(self):
        return action.get_actions()

    # IAuthFunctions
    def get_auth_functions(self):
        return auth.get_auth_functions()

    # IValidators
    def get_validators(self):
        return validators.get_validators()

    # IBlueprint
    def get_blueprint(self):
        return views.get_blueprints()

    # ITemplateHelpers
    def get_helpers(self):
        return helpers.get_helpers()

    # IClick
    def get_commands(self):
        return cli.get_commands()


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
            storage = base.storage_from_settings(name, settings)
        except exceptions.UnknownAdapterError as err:
            raise CkanConfigurationException(str(err))  # noqa: B904

        base.storages.register(name, storage)
