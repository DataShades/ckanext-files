from __future__ import annotations

from typing import Any

from dominate import tags

import ckan.plugins.toolkit as tk

from ckanext.ap_main.collection.base import (
    ApCollection,
    ApColumns,
    ApHtmxTableSerializer,
    BulkAction,
    RowAction,
)
from ckanext.collection.types import ButtonFilter, InputFilter
from ckanext.collection.utils import Filters
from ckanext.collection.utils.data.model import ModelData

from ckanext.files.model import File


def file_row_dictizer(serializer: ApHtmxTableSerializer[Any], row: File):
    data = row.dictize({})
    data["bulk-action"] = data["id"]

    return data


class FileManagerCollection(ApCollection):
    SerializerFactory = ApHtmxTableSerializer.with_attributes(
        record_template="file_manager/record.html",
        row_dictizer=file_row_dictizer,
    )

    ColumnsFactory = ApColumns.with_attributes(
        names=[
            "bulk-action",
            "name",
            "path",
            "kind",
            "uploaded_at",
            "last_access",
            "extras",
            "row_actions",
        ],
        sortable={"name", "kind", "uploaded_at", "last_access"},
        searchable={"name"},
        labels={
            "bulk-action": tk.literal(
                tags.input_(
                    type="checkbox",
                    name="bulk_check",
                    id="bulk_check",
                    data_module="ap-bulk-check",
                    data_module_selector='input[name="entity_id"]',
                ),
            ),
            "name": "Name",
            "path": "Path",
            "kind": "Type",
            "uploaded_at": "Uploaded At",
            "last_access": "Last Access",
            "extras": "Extras",
            "row_actions": "Actions",
        },
        width={"name": "20%", "path": "20%"},
        serializers={
            "uploaded_at": [("date", {})],
            "extras": [("json_display", {})],
            "last_access": [("day_passed", {})],
        },
    )

    DataFactory = ModelData.with_attributes(
        model=File,
        is_scalar=True,
        use_naive_search=True,
        use_naive_filters=True,
    )

    FiltersFactory = Filters.with_attributes(
        static_actions=[
            BulkAction(
                name="bulk-action",
                type="bulk_action",
                options={
                    "label": "Action",
                    "options": [
                        {"value": "1", "text": "Remove selected files"},
                    ],
                },
            ),
            RowAction(
                name="edit",
                type="row_action",
                options={
                    "endpoint": "",
                    "label": "",
                    "icon": "fa fa-pencil",
                    "params": {
                        "data-module-path": "$id",
                        "view": "edit",
                    },
                },
            ),
            RowAction(
                name="view",
                type="row_action",
                options={
                    "endpoint": "ap_content.entity_proxy",
                    "label": "View",
                    "params": {
                        "entity_id": "$id",
                        "entity_type": "$type",
                        "view": "read",
                    },
                },
            ),
        ],
        static_filters=[
            InputFilter(
                name="q",
                type="input",
                options={
                    "label": "Search",
                    "placeholder": "Search",
                },
            ),
            ButtonFilter(
                name="type",
                type="button",
                options={
                    "label": "Clear",
                    "type": "button",
                    "attrs": {
                        "onclick": (
                            "$(this).closest('form').find('input,select')"
                            ".val('').prevObject[0].requestSubmit()"
                        ),
                    },
                },
            ),
        ],
    )
