from ckan.logic.schema import validator_args
from ckan.types import Schema, Validator, ValidatorFactory

from ckanext.files import config


@validator_args
def file_create(
    ignore_empty: Validator,
    unicode_safe: Validator,
    default: ValidatorFactory,
    files_into_upload: Validator,
    not_missing: Validator,
    files_ensure_name: ValidatorFactory,
) -> Schema:
    # name is checked inside action, using "upload" as source if empty
    return {
        "name": [ignore_empty, unicode_safe],
        "storage": [default(config.default_storage()), unicode_safe],
        "upload": [not_missing, files_into_upload, files_ensure_name("name")],
    }


@validator_args
def _base_file_search(
    unicode_safe: Validator,
    default: ValidatorFactory,
    int_validator: Validator,
    boolean_validator: Validator,
    ignore_empty: Validator,
) -> Schema:
    return {
        "start": [default(0), int_validator],
        "rows": [default(10), int_validator],
        "sort": [default("name"), unicode_safe],
        "reverse": [boolean_validator],
        "storage_data": [ignore_empty],
        "plugin_data": [ignore_empty],
    }


@validator_args
def file_search_by_user(
    ignore_missing: Validator,
    unicode_safe: Validator,
    default: ValidatorFactory,
    ignore_not_sysadmin: Validator,
) -> Schema:
    schema = _base_file_search()
    schema["user"] = [ignore_missing, ignore_not_sysadmin, unicode_safe]
    return schema


@validator_args
def file_search(default: ValidatorFactory, boolean_validator: Validator) -> Schema:
    schema = _base_file_search()
    schema["completed"] = [default(True), boolean_validator]
    return schema


@validator_args
def file_delete(
    default: ValidatorFactory,
    boolean_validator: Validator,
    not_empty: Validator,
    unicode_safe: Validator,
) -> Schema:
    return {
        "id": [not_empty, unicode_safe],
        "completed": [default(True), boolean_validator],
    }


@validator_args
def file_show(
    default: ValidatorFactory,
    boolean_validator: Validator,
    not_empty: Validator,
    unicode_safe: Validator,
) -> Schema:
    return {
        "id": [not_empty, unicode_safe],
        "completed": [default(True), boolean_validator],
    }


@validator_args
def file_rename(
    default: ValidatorFactory,
    boolean_validator: Validator,
    not_empty: Validator,
    unicode_safe: Validator,
) -> Schema:
    return {
        "id": [not_empty, unicode_safe],
        "name": [not_empty, unicode_safe],
        "completed": [default(True), boolean_validator],
    }


@validator_args
def multipart_start(
    not_empty: Validator,
    unicode_safe: Validator,
    default: ValidatorFactory,
    int_validator: Validator,
) -> Schema:
    return {
        "storage": [default(config.default_storage()), unicode_safe],
        "name": [not_empty, unicode_safe],
        "content_type": [not_empty, unicode_safe],
        "size": [not_empty, int_validator],
        "hash": [default(""), unicode_safe],
    }


@validator_args
def multipart_refresh(not_empty: Validator, unicode_safe: Validator) -> Schema:
    return {
        "id": [not_empty, unicode_safe],
    }


@validator_args
def multipart_update(not_empty: Validator, unicode_safe: Validator) -> Schema:
    return {
        "id": [not_empty, unicode_safe],
    }


@validator_args
def multipart_complete(not_empty: Validator, unicode_safe: Validator) -> Schema:
    return {
        "id": [not_empty, unicode_safe],
    }
