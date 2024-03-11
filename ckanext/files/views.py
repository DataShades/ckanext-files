import logging
from functools import partial

from flask import Blueprint
from flask.views import MethodView

import ckan.plugins.toolkit as tk
from ckan.lib.helpers import Page

from ckanext.files import types  # isort: skip # noqa: F401

log = logging.getLogger(__name__)
bp = Blueprint("files", __name__)


def not_found_handler(error: tk.ObjectNotFound):
    """Generic handler for ObjectNotFound exception"""
    return (
        tk.render(
            "error_document_template.html",
            {
                "code": 404,
                "content": f"Object not found: {error.message}",
                "name": "Not found",
            },
        ),
        404,
    )


def not_authorized_handler(error: tk.NotAuthorized):
    """Generic handler for NotAuthorized exception"""
    return (
        tk.render(
            "error_document_template.html",
            {
                "code": 403,
                "content": error.message or "Not authorized to view this page",
                "name": "Not authorized",
            },
        ),
        403,
    )


bp.register_error_handler(tk.ObjectNotFound, not_found_handler)
bp.register_error_handler(tk.NotAuthorized, not_authorized_handler)


def get_blueprints():
    return [bp]


def _pager_url(*args, **kwargs):
    # type: (*types.Any, **types.Any) -> str
    """Generic URL builder for `url` parameter of ckan.lib.pagination.Page.

    It generates pagination link keeping all the parameters from URL and query
    string.
    """
    params = {k: v for k, v in tk.request.args.items() if k != "page"}
    params.update({k: v for k, v in (tk.request.view_args or {}).items()})
    params.update(kwargs)
    return tk.h.pager_url(*args, **params)


@bp.route("/user/<user_id>/files")
def user(user_id):
    # type: (str) -> str
    user_dict = tk.get_action("user_show")({}, {"id": user_id})

    rows = 10
    params = tk.request.params  # type: ignore
    page = tk.h.get_page_number(params)
    start = rows * page - rows
    try:
        files = tk.get_action("files_file_search_by_user")(
            {},
            {
                "rows": rows,
                "start": start,
                "user": user_id,
                "sort": params.get("sort", "ctime"),
                "reverse": params.get("reverse", True),
            },
        )  # type: dict[str, types.Any]
    except tk.ValidationError as err:
        for k, v in err.error_summary.items():
            tk.h.flash_error("{}: {}".format(k, v))

        files = {"count": 0, "results": []}

    pager = Page(
        [],
        items_per_page=rows,
        page=page,
        item_count=files["count"],
        url=partial(_pager_url),
    )

    return tk.render(
        "files/user.html",
        {
            "user_dict": user_dict,
            "files": files,
            "pager": pager,
        },
    )


class DeleteFile(MethodView):
    def post(self, user_id, file_id):
        # type: (str, str) -> types.Any
        tk.get_action("files_file_delete")({}, {"id": file_id})
        return tk.redirect_to("files.user", user_id=user_id)

    def get(self, user_id, file_id):
        # type: (str, str) -> types.Any

        tk.check_access("files_file_delete", {}, {"id": file_id})
        info = tk.get_action("files_file_show")({}, {"id": file_id})
        user_dict = tk.get_action("user_show")({}, {"id": user_id})

        return tk.render(
            "files/delete.html",
            {
                "file": info,
                "user_dict": user_dict,
            },
        )


bp.add_url_rule(
    "/user/<user_id>/files/delete/<file_id>",
    view_func=DeleteFile.as_view("delete_file"),
)
