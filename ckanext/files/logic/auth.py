import ckan.plugins.toolkit as tk
from ckanext.toolbelt.decorators import Collector

auth, get_auth_functions = Collector("files").split()


@auth
def file_create(context, data_dict):
    {"success": False}


@auth
def file_update(context, data_dict):
    {"success": False}


@auth
def file_delete(context, data_dict):
    {"success": False}


@auth
@tk.auth_allow_anonymous_access
@tk.side_effect_free
def file_show(context, data_dict):
    {"success": True}
