import logging
from functools import partial

from flask import Blueprint
from flask.views import MethodView

import ckan.plugins.toolkit as tk
from ckan.lib.helpers import Page

from ckanext.files import types  # isort: skip # noqa: F401

log = logging.getLogger(__name__)
bp = Blueprint("files", __name__)


def not_found_handler(error):
    # type: (tk.ObjectNotFound) -> tuple[str, int]
    """Generic handler for ObjectNotFound exception"""
    return (
        tk.render(
            "error_document_template.html",
            {
                "code": 404,
                "content": "Object not found: {}".format(error.message),
                "name": "Not found",
            },
        ),
        404,
    )


def not_authorized_handler(error):
    # type: (tk.NotAuthorized) -> tuple[str, int]
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
@bp.route("/user/<user_id>/files/storage/<storage>")
def user(user_id, storage=None):
    # type: (str, str | None) -> str
    user_dict = tk.get_action("user_show")(
        {},
        {"id": user_id, "include_num_followers": True},
    )

    rows = 10
    params = tk.request.params  # type: ignore
    page = tk.h.get_page_number(params)
    start = rows * page - rows

    search_dict = {
        "rows": rows,
        "start": start,
        "user": user_id,
        "sort": params.get("sort", "ctime"),
        "reverse": params.get("reverse", True),
    }  # type: dict[str, types.Any]

    if storage:
        search_dict["storage"] = storage

    try:
        files = tk.get_action("files_file_search_by_user")({}, search_dict)
    except tk.ValidationError as err:
        for k, v in err.error_summary.items():
            tk.h.flash_error("{}: {}".format(k, v))

        files = {"count": 0, "results": []}  # type: dict[str, types.Any]

    pager = Page(
        [],
        items_per_page=rows,
        page=page,
        item_count=files["count"],
        url=partial(_pager_url),
    )

    tpl_names = ["files/user/index.html"]
    tpl_data = {
        "user_dict": user_dict,
        "files": files,
        "pager": pager,
    }  # type: dict[str, types.Any]

    if storage:
        tpl_data["storage"] = storage
        tpl_names.insert(0, "files/user/index.{}.html".format(storage))

    return tk.render(tpl_names, tpl_data)  # type: ignore


class DeleteFile(MethodView):
    def post(self, user_id, file_id):
        # type: (str, str) -> types.Any
        tk.get_action("files_file_delete")({}, {"id": file_id})

        came_from = tk.h.get_request_param("came_from")
        if came_from:
            return tk.redirect_to(came_from)

        return tk.redirect_to("files.user", user_id=user_id)

    def get(self, user_id, file_id):
        # type: (str, str) -> types.Any

        tk.check_access("files_file_delete", {}, {"id": file_id})
        info = tk.get_action("files_file_show")({}, {"id": file_id})
        user_dict = tk.get_action("user_show")(
            {},
            {"id": user_id, "include_num_followers": True},
        )

        return tk.render(
            "files/user/delete.html",
            {
                "file": info,
                "user_dict": user_dict,
            },
        )


bp.add_url_rule(
    "/user/<user_id>/files/delete/<file_id>",
    view_func=DeleteFile.as_view("delete_file"),
)
