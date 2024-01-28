from __future__ import annotations

from typing import Any

from dominate import tags

import ckan.plugins.toolkit as tk
import sqlalchemy as sa

from ckanext.collection.types import InputFilter, LinkFilter
from ckanext.collection.utils import Filters, StatementSaData

from ckanext.ap_main.collection.base import (
    ApCollection,
    ApColumns,
    BulkAction,
    RowAction,
    ApHtmxTableSerializer,
)

from ckanext.files.model import File


class FileManagerCollection(ApCollection[Any]):
    SerializerFactory = ApHtmxTableSerializer.with_attributes(
        record_template="file_manager/record.html"
    )

    ColumnsFactory = ApColumns.with_attributes(
        names=[
            "bulk-action",
            "name",
            "path",
            "kind",
            "uploaded_at",
            "extras",
            "row_actions",
        ],
        sortable={"name", "kind", "uploaded_at"},
        searchable={"name"},
        labels={
            "bulk-action": tk.literal(
                tags.input_(
                    type="checkbox",
                    name="bulk_check",
                    id="bulk_check",
                    data_module="ap-bulk-check",
                    data_module_selector='input[name="id"]',
                )
            ),
            "name": "Name",
            "path": "Path",
            "kind": "Type",
            "uploaded_at": "Uploaded At",
            "extras": "Extras",
            "row_actions": "Actions",
        },
        width={"name": "20%", "path": "20%"},
        serializers={
            "uploaded_at": [("date", {})],
            "extras": [("json_display", {})],
        },
    )

    DataFactory = StatementSaData.with_attributes(
        model=File,
        use_naive_filters=True,
        use_naive_search=True,
        statement=sa.select(
            File.id.label("bulk-action"),
            File.id.label("id"),
            File.name.label("name"),
            File.path.label("path"),
            File.kind.label("kind"),
            File.uploaded_at.label("uploaded_at"),
            File.extras.label("extras"),
        ),
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
                        "entity_type": "$type",
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
            LinkFilter(
                name="clear",
                type="link",
                options={
                    "label": "Clear",
                    "endpoint": "file_manager.list",
                    "kwargs": {},
                },
            ),
        ],
    )
