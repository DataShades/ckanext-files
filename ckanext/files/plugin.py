import six

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

if six.PY3:
    from typing import Any  # isort: skip # noqa: F401


class FilesPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurable)
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)
    p.implements(p.IValidators)
    p.implements(p.IBlueprint)
    p.implements(p.ITemplateHelpers)

    if tk.check_ckan_version("2.9"):
        p.implements(p.IClick)

    p.implements(interfaces.IFiles)

    # IFiles
    def files_get_storage_adapters(self):
        # type: () -> dict[str, Any]
        adapters = {}  # type: dict[str, Any]
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
        # type: (Any) -> None
        base.adapters.reset()
        for plugin in p.PluginImplementations(interfaces.IFiles):
            for name, adapter in plugin.files_get_storage_adapters().items():
                base.adapters.register(name, adapter)

        base.storages.reset()
        for name, settings in config.storages().items():
            try:
                storage = base.storage_from_settings(settings)
            except exceptions.UnknownAdapterError as err:
                raise CkanConfigurationException(str(err))  # noqa: B904

            base.storages.register(name, storage)

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


if tk.check_ckan_version("2.10"):
    FilesPlugin = tk.blanket.config_declarations(FilesPlugin)
