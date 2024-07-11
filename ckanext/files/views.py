from __future__ import annotations

import logging
from functools import partial
from typing import Any

import jwt
from flask import Blueprint, jsonify

import ckan.plugins.toolkit as tk
from ckan import model
from ckan.common import streaming_response
from ckan.lib.helpers import Page
from ckan.logic import parse_params
from ckan.types import Response
from ckan.views.resource import download

from ckanext.files import shared, utils

log = logging.getLogger(__name__)
bp = Blueprint("files", __name__)

__all__ = ["bp"]


def not_found_handler(error: tk.ObjectNotFound) -> tuple[str, int]:
    """Generic handler for ObjectNotFound exception."""
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


def not_authorized_handler(error: tk.NotAuthorized) -> tuple[str, int]:
    """Generic handler for NotAuthorized exception."""
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


@bp.route("/file/download/<file_id>")
def dispatch_download(file_id: str) -> Response:
    tk.check_access("files_file_download", {}, {"id": file_id})
    item = model.Session.get(shared.File, file_id)
    if not item:
        raise tk.ObjectNotFound("file")

    storage = shared.get_storage(item.storage)
    data = shared.FileData.from_model(item)

    # do not use permanent link here as it nerver expires and user who got it
    # once will be able to download file as long as it exists.
    link = (
        storage.public_link(data)
        or storage.one_time_link(data)
        or storage.temporal_link(data)
    )

    if link:
        return tk.redirect_to(link)

    if resp := _streaming_file(item, storage, data):
        return resp

    return tk.abort(422, "File is not downloadable")


def _streaming_file(
    item: shared.File,
    storage: shared.Storage,
    data: shared.FileData,
) -> Response | None:
    if storage.supports(shared.Capability.STREAM):
        resp = streaming_response(storage.stream(data), data.content_type)
        if utils.is_supported_type(item.content_type, shared.config.inline_types()):
            resp.headers["content-disposition"] = f"inline; filename={item.name}"
        else:
            resp.headers["content-disposition"] = f"attachment; filename={item.name}"

        item.touch()
        model.Session.commit()

        return resp


@bp.route("/file/token-download/<token>")
def temporal_download(token: str) -> Response:
    try:
        data = utils.decode_token(token)

    except jwt.ExpiredSignatureError as err:
        log.debug("Expired file-download token: %s", err)
        raise tk.ObjectNotFound("file") from err

    except jwt.InvalidTokenError as err:
        log.debug("Cannot decode file-download token: %s", err)
        raise tk.ObjectNotFound("file") from err

    if data.get("topic") != "download_file":
        raise tk.ObjectNotFound("file")

    if "id" in data:
        item = model.Session.get(shared.File, data["sub"])
    elif "location" in data:
        item = model.Session.scalar(
            shared.File.by_location(data["location"], data.get("storage")),
        )
    else:
        item = None

    if not item:
        raise tk.ObjectNotFound("file")

    storage = shared.get_storage(item.storage)
    data = shared.FileData.from_model(item)

    if resp := _streaming_file(item, storage, data):
        return resp

    return tk.abort(422, "File is not downloadable")


def _pager_url(*args: Any, **kwargs: Any) -> str:
    """Generic URL builder for `url` parameter of ckan.lib.pagination.Page.

    It generates pagination link keeping all the parameters from URL and query
    string.
    """
    params = {k: v for k, v in tk.request.args.items() if k != "page"}
    view_args: dict[str, Any] = tk.request.view_args or {}
    params.update(
        dict(view_args.items()),
    )
    params.update(kwargs)
    return tk.h.pager_url(*args, **params)


@bp.route("/<owner_type>/<owner_id>/files/list")
def list_files(owner_type: str, owner_id: str) -> str:
    owner = utils.get_owner(owner_type, owner_id)
    if owner and hasattr(owner, "id"):
        owner_id = owner.id

    rows = 10
    params = tk.request.args
    page = tk.h.get_page_number(params)
    start = rows * page - rows

    search_dict: dict[str, Any] = {
        "rows": rows,
        "start": start,
        "owner_type": owner_type,
        "owner_id": owner_id,
        "sort": params.get("sort", "ctime"),
        "reverse": params.get("reverse", True),
    }

    if "storage" in params:
        search_dict["storage"] = params["storage"]

    result: dict[str, Any]
    try:
        result = tk.get_action("files_file_scan")({}, search_dict)
    except tk.ValidationError as err:
        for k, v in err.error_summary.items():
            tk.h.flash_error(f"{k}: {v}")

        result = {"count": 0, "results": []}

    pager = Page(
        result["results"],
        items_per_page=rows,
        page=page,
        item_count=result["count"],
        url=partial(_pager_url),
    )

    tpl_data: dict[str, Any] = {
        "owner": owner,
        "pager": pager,
        "owner_type": owner_type,
        "owner_id": owner_id,
    }

    return tk.render("files/index.html", tpl_data)


@bp.route("/<owner_type>/<owner_id>/files/delete/<file_id>", methods=["POST", "GET"])
def delete_file(
    owner_type: str,
    owner_id: str,
    file_id: str,
) -> str | shared.types.Response:
    if tk.request.method == "POST":
        try:
            tk.get_action("files_file_delete")({}, {"id": file_id})
        except tk.NotAuthorized as err:
            tk.h.flash_error(err)
        else:
            came_from = tk.h.get_request_param("came_from")
            if came_from:
                return tk.redirect_to(came_from)

            return tk.redirect_to(
                "files.list_files",
                owner_type=owner_type,
                owner_id=owner_id,
            )

    tk.check_access("files_file_delete", {}, {"id": file_id})
    info = tk.get_action("files_file_show")({}, {"id": file_id})
    return tk.render("files/delete.html", {"file": info})


@bp.route("/api/util/files_autocomplete_own_files")
def autocomplete_own_files() -> Any:
    tk.check_access("files_autocomplete_available_resource_files", {}, {})

    params = parse_params(tk.request.args)

    q = params.pop("q", "")

    params.update(
        {
            "owner_type": "user",
            "owner_id": tk.current_user.is_authenticated and tk.current_user.id,  # type: ignore
            "pinned": False,
            "name": ["like", f"%{q}%"],
        },
    )

    result = tk.get_action("files_file_search")(
        {"ignore_auth": True},
        params,
    )

    return jsonify(
        {
            "ResultSet": {
                "Result": [
                    dict(
                        item,
                        label="{name} [{content_type}, {size}]".format(
                            name=item["name"],
                            content_type=tk.h.unified_resource_format(
                                item["content_type"],
                            ),
                            size=utils.humanize_filesize(item["size"]),
                        ),
                    )
                    for item in result["results"]
                ],
            },
        },
    )


@bp.route("/api/util/files_autocomplete_available_resource_files")
def autocomplete_available_resource_files() -> Any:
    tk.check_access("files_autocomplete_available_resource_files", {}, {})
    q = tk.request.args.get("incomplete")

    result = tk.get_action("files_file_search")(
        {"ignore_auth": True},
        {
            "owner_type": "user",
            "owner_id": tk.current_user.is_authenticated and tk.current_user.id,  # type: ignore
            "pinned": False,
            "storage": shared.config.resources_storage(),
            "name": ["like", f"%{q}%"],
        },
    )

    return jsonify(
        {
            "ResultSet": {
                "Result": [
                    {
                        "id": item["id"],
                        "name": item["name"],
                        "label": "{name} [{content_type}, {size}]".format(
                            name=item["name"],
                            content_type=tk.h.unified_resource_format(
                                item["content_type"],
                            ),
                            size=utils.humanize_filesize(item["size"]),
                        ),
                    }
                    for item in result["results"]
                ],
            },
        },
    )


@bp.route(
    "/<package_type>/<id>/resource/<resource_id>/download",
    defaults={"package_type": "dataset"},
)
@bp.route(
    "/<package_type>/<id>/<resource_id>/download/<filename>",
    defaults={"package_type": "dataset"},
)
def resource_download(
    package_type: str,
    id: str,
    resource_id: str,
    filename: str | None = None,
):
    try:
        resource = tk.get_action("resource_show")({}, {"id": resource_id})
    except tk.ObjectNotFound:
        return tk.abort(404, tk._("Resource not found"))
    except tk.NotAuthorized:
        return tk.abort(403, tk._("Not authorized to download resource"))

    if resource.get("url_type") != "file":
        return download(package_type, id, resource_id, filename)

    file_id = resource["url"].rsplit("/", 1)[-1]
    return dispatch_download(file_id)
