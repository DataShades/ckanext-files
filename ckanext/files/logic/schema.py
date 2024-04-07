from ckan.logic.schema import validator_args

from ckanext.files import config

from ckanext.files import types  # isort: skip # noqa: F401


@validator_args
def file_create(ignore_empty, unicode_safe, default, files_into_upload, not_missing):
    # type: (types.Any, types.Any, types.Any, types.Any, types.Any) -> types.Any

    # name is checked inside action, using "upload" as source if empty
    return {
        "name": [ignore_empty, unicode_safe],
        "storage": [default(config.default_storage()), unicode_safe],
        "upload": [not_missing, files_into_upload],
    }


@validator_args
def _base_file_search(
    unicode_safe,
    default,
    int_validator,
    boolean_validator,
    ignore_empty,
):
    # type: (types.Any, types.Any, types.Any, types.Any, types.Any) -> types.Any

    return {
        "start": [default(0), int_validator],
        "rows": [default(10), int_validator],
        "sort": [default("name"), unicode_safe],
        "reverse": [boolean_validator],
        "storage": [ignore_empty, unicode_safe],
        "storage_data": [ignore_empty],
        "plugin_data": [ignore_empty],
    }


@validator_args
def file_search_by_user(ignore_missing, unicode_safe, default, ignore_not_sysadmin):
    # type: (types.Any, types.Any, types.Any, types.Any) -> types.Any
    schema = _base_file_search()
    schema["user"] = [ignore_missing, ignore_not_sysadmin, unicode_safe]
    return schema


@validator_args
def file_delete(not_empty, unicode_safe):
    # type: (types.Any, types.Any) -> types.Any
    return {
        "id": [not_empty, unicode_safe],
    }


@validator_args
def file_show(not_empty, unicode_safe):
    # type: (types.Any, types.Any) -> types.Any
    return {
        "id": [not_empty, unicode_safe],
    }


@validator_args
def file_rename(not_empty, unicode_safe):
    # type: (types.Any, types.Any) -> types.Any
    return {
        "id": [not_empty, unicode_safe],
        "name": [not_empty, unicode_safe],
    }


@validator_args
def upload_initialize(ignore_empty, unicode_safe, default, int_validator, not_missing):
    # type: (types.Any, types.Any, types.Any, types.Any, types.Any) -> types.Any

    # name is checked inside action, using "upload" as source if empty
    return {
        "name": [ignore_empty, unicode_safe],
        "storage": [default(config.default_storage()), unicode_safe],
    }


@validator_args
def upload_show(not_empty, unicode_safe):
    # type: (types.Any, types.Any) -> types.Any
    return {
        "id": [not_empty, unicode_safe],
    }


@validator_args
def upload_update(not_empty, unicode_safe):
    # type: (types.Any, types.Any) -> types.Any
    return {
        "id": [not_empty, unicode_safe],
    }


@validator_args
def upload_complete(not_empty, unicode_safe):
    # type: (types.Any, types.Any) -> types.Any
    return {
        "id": [not_empty, unicode_safe],
    }
