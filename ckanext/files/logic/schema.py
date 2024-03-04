import six

from ckan.logic.schema import validator_args

from ckanext.files import config

if six.PY3:
    from typing import Any  # isort: skip


@validator_args
def file_create(not_empty, unicode_safe, default, files_into_upload, not_missing):
    # type: (Any, Any, Any, Any, Any) -> Any
    return {
        "name": [not_empty, unicode_safe],
        "storage": [default(config.default_storage()), unicode_safe],
        "upload": [not_missing, files_into_upload],
    }


@validator_args
def file_delete(not_empty, unicode_safe):
    # type: (Any, Any) -> Any
    return {
        "id": [not_empty, unicode_safe],
    }


@validator_args
def file_show(not_empty, unicode_safe):
    # type: (Any, Any) -> Any
    return {
        "id": [not_empty, unicode_safe],
    }


@validator_args
def upload_initialize(not_empty, unicode_safe, default, int_validator, not_missing):
    # type: (Any, Any, Any, Any, Any) -> Any
    return {
        "name": [not_empty, unicode_safe],
        "storage": [default(config.default_storage()), unicode_safe],
    }


@validator_args
def upload_update(not_empty, unicode_safe):
    # type: (Any, Any) -> Any
    return {
        "id": [not_empty, unicode_safe],
    }


@validator_args
def upload_complete(not_empty, unicode_safe):
    # type: (Any, Any) -> Any
    return {
        "id": [not_empty, unicode_safe],
    }
