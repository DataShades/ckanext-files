from __future__ import annotations

from datetime import datetime

import ckan.plugins.toolkit as tk

from ckanext.toolbelt.decorators import Collector

import ckanext.ap_main.types as ap_types

renderer, get_renderers = Collector("fm").split()


@renderer
def last_access(
    rows: ap_types.ItemList,
    row: ap_types.Item,
    value: ap_types.ItemValue,
    **kwargs,
) -> int:
    if not value:
        return tk._("Never")

    datetime_obj = datetime.fromisoformat(value)
    current_date = datetime.now()

    days_passed = (current_date - datetime_obj).days

    return days_passed
