import six
import ckan.plugins as p
import ckan.plugins.toolkit as tk

from ckanext.files import (
    views,
    helpers,
    cli,
    shared,
    config,
    utils,
    interfaces,
    storage,
)
from ckanext.files.logic import action, auth, validators

if six.PY3:  # pragma: no cover
    from typing import Any


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
        }

        if hasattr(storage, "GoogleCloudStorage"):
            adapters.update({"files:google_cloud_storage": storage.GoogleCloudStorage})

        return adapters

    # IConfigurable
    def configure(self, config_):
        # type: (Any) -> None
        utils.adapters.reset()
        for plugin in p.PluginImplementations(interfaces.IFiles):
            for name, adapter in plugin.files_get_storage_adapters().items():
                utils.adapters.register(name, adapter)

        shared.storages.reset()
        for name, settings in config.storages().items():
            storage = utils.storage_from_settings(settings)
            shared.storages.register(name, storage)

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
