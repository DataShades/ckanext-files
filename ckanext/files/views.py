import logging

from flask import Blueprint
from flask.views import MethodView

import ckan.plugins.toolkit as tk


log = logging.getLogger(__name__)
files = Blueprint("files", __name__)


class FilesGetFileView(MethodView):
    """This view is designed for serving files while also updating
    the 'last_access' field in the database for the corresponding file object.

    The `last_access` field is updated inside `files_file_show` action.
    """

    def get(self, file_id: str):
        try:
            file_data = tk.get_action("files_file_show")(
                {
                    "user": tk.current_user.name,
                    "auth_user_obj": tk.current_user,
                },
                {"id": file_id},
            )
        except (tk.ValidationError, OSError):
            return

        return tk.redirect_to(
            tk.h.url_for_static(file_data["path"], qualified=True)
        )


files.add_url_rule(
    "/files/get_url/<file_id>",
    view_func=FilesGetFileView.as_view("get_file"),
)
