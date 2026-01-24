import ckan.plugins.toolkit as tk
from ckan import types


def file_widget_file_create(context: types.Context, data_dict: types.DataDict) -> None:
    data_dict["storage"] = "default"
    return tk.get_action("files_file_create")(context, data_dict)


def file_widget_link_create(context: types.Context, data_dict: types.DataDict) -> None:
    data_dict["storage"] = "link"
    return tk.get_action("files_file_create")(context, data_dict)
