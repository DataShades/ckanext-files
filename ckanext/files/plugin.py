import ckan.plugins as p
import ckan.plugins.toolkit as tk

from .logic import action, auth, schema


class FilesPlugin(p.SingletonPlugin):
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)

    if tk.check_ckan_version("2.10"):
        p.implements(p.IConfigDeclaration)

        def declare_config_options(self, declaration, key):
            kind = tk.config.get(schema.CONFIG_KIND, schema.DEFAULT_KIND)
            declaration.declare_list(f"ckan.upload.{kind}.types", [])
            declaration.declare_list(f"ckan.upload.{kind}.mimetypes", [])

    # IActions
    def get_actions(self):
        return action.get_actions()

    # IAuthFunctions
    def get_auth_functions(self):
        return auth.get_auth_functions()
