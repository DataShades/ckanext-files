from ckan.logic.schema import validator_args
from ckan.types import Schema, Validator, ValidatorFactory

from ckanext.files import shared


@validator_args
def file_create(  # noqa: PLR0913
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
        "storage": [default(shared.config.default_storage()), unicode_safe],
        "upload": [not_missing, files_into_upload, files_ensure_name("name")],
    }


@validator_args
def file_replace(  # noqa: PLR0913
    unicode_safe: Validator,
    files_into_upload: Validator,
    not_missing: Validator,
) -> Schema:
    return {
        "id": [not_missing, unicode_safe],
        "upload": [not_missing, files_into_upload],
    }


@validator_args
def _base_file_search(  # noqa: PLR0913
    unicode_safe: Validator,
    default: ValidatorFactory,
    int_validator: Validator,
    boolean_validator: Validator,
    ignore_empty: Validator,
    dict_only: Validator,
    ignore_missing: Validator,
    convert_to_json_if_string: Validator,
) -> Schema:
    return {
        "start": [default(0), int_validator],
        "rows": [default(10), int_validator],
        "sort": [default("name"), unicode_safe],
        "reverse": [boolean_validator],
        "storage_data": [ignore_empty, convert_to_json_if_string, dict_only],
        "plugin_data": [ignore_empty, convert_to_json_if_string, dict_only],
        "owner_type": [ignore_empty],
        "owner_id": [ignore_empty],
        "pinned": [ignore_missing, boolean_validator],
    }


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
        "storage": [default(shared.config.default_storage()), unicode_safe],
        "name": [not_empty, unicode_safe],
        "content_type": [not_empty, unicode_safe],
        "size": [not_empty, int_validator],
        "hash": [default(""), unicode_safe],
    }


@validator_args
def multipart_refresh(not_empty: Validator, unicode_safe: Validator) -> Schema:
    return {"id": [not_empty, unicode_safe]}


@validator_args
def multipart_update(not_empty: Validator, unicode_safe: Validator) -> Schema:
    return {"id": [not_empty, unicode_safe]}


@validator_args
def multipart_complete(not_empty: Validator, unicode_safe: Validator, boolean_validator: Validator) -> Schema:
    return {
        "id": [not_empty, unicode_safe],
        "keep_storage_data": [boolean_validator],
        "keep_plugin_data": [boolean_validator]
    }


@validator_args
def transfer_ownership(
    not_empty: Validator,
    boolean_validator: Validator,
    default: ValidatorFactory,
    unicode_safe: Validator,
) -> Schema:
    return {
        "id": [not_empty, unicode_safe],
        "completed": [default(True), boolean_validator],
        "owner_id": [not_empty, unicode_safe],
        "owner_type": [not_empty, unicode_safe],
        "force": [default(False), boolean_validator],
        "pin": [default(False), boolean_validator],
    }


@validator_args
def file_scan(
    default: ValidatorFactory,
    unicode_safe: Validator,
) -> Schema:
    return {
        "owner_id": [default(""), unicode_safe],
        "owner_type": [default("user"), unicode_safe],
    }


@validator_args
def file_pin(
    boolean_validator: Validator,
    default: ValidatorFactory,
    not_empty: Validator,
    unicode_safe: Validator,
) -> Schema:
    return {
        "id": [not_empty, unicode_safe],
        "completed": [default(True), boolean_validator],
    }


@validator_args
def file_unpin(
    boolean_validator: Validator,
    default: ValidatorFactory,
    not_empty: Validator,
    unicode_safe: Validator,
) -> Schema:
    return {
        "id": [not_empty, unicode_safe],
        "completed": [default(True), boolean_validator],
    }


@validator_args
def resource_upload(ignore: Validator) -> Schema:
    schema = file_create()
    schema["storage"] = [ignore]
    schema["__extras"] = [ignore]
    return schema


@validator_args
def group_image_upload(ignore: Validator) -> Schema:
    schema = file_create()
    schema["storage"] = [ignore]
    schema["__extras"] = [ignore]
    return schema


@validator_args
def user_image_upload(ignore: Validator) -> Schema:
    schema = file_create()
    schema["storage"] = [ignore]
    schema["__extras"] = [ignore]
    return schema
