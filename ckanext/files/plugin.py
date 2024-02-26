
import ckan.plugins as p
import ckan.plugins.toolkit as tk

from .logic import action, auth, schema


@tk.blanket.blueprints
@tk.blanket.config_declarations
@tk.blanket.cli
@tk.blanket.helpers
class FilesPlugin(p.SingletonPlugin):
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)

    # IActions
    def get_actions(self):
        return action.get_actions()

    # IAuthFunctions
    def get_auth_functions(self):
        return auth.get_auth_functions()
