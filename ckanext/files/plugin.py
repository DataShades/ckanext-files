import ckan.plugins as plugins


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
