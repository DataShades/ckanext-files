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
