import ckan.plugins as p
import ckan.plugins.toolkit as tk

from ckanext.files import views, helpers, cli
from ckanext.files.logic import action, auth


class FilesPlugin(p.SingletonPlugin):
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)
    p.implements(p.IBlueprint)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IClick)

    # IActions
    def get_actions(self):
        return action.get_actions()

    # IAuthFunctions
    def get_auth_functions(self):
        return auth.get_auth_functions()

    def get_blueprint(self):
        return views.get_blueprints()

    def get_helpers(self):
        return helpers.get_helpers()

    def get_commands(self):
        return cli.get_commands()


if tk.check_ckan_version("2.10"):
    FilesPlugin = tk.blanket.config_declarations(FilesPlugin)
