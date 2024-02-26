from ckanext.toolbelt.decorators import Collector

auth, get_auth_functions = Collector("files").split()


@auth
def file_create(context, data_dict):
    return {"success": False}


@auth
def file_update(context, data_dict):
    return {"success": False}


@auth
def file_delete(context, data_dict):
    return {"success": False}


@auth
def file_show(context, data_dict):
    return {"success": True}


@auth
def get_unused_files(context, data_dict):
    return {"success": False}
