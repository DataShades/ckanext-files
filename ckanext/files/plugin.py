import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

from .logic import action, auth


class FilesPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IAuthFunctions)

    # IActions
    def get_actions(self):
        return action.get_actions()

    # IAuthFunctions
    def get_auth_functions(self):
        return auth.get_auth_functions()

    # plugins.implements(plugins.IConfigurer)
    # IConfigurer
    # def update_config(self, config_):
    #     toolkit.add_template_directory(config_, "templates")
    #     toolkit.add_public_directory(config_, "public")
    #     toolkit.add_resource("assets", "files")
