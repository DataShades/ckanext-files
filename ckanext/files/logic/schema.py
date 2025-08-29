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
) -> Schema:
    # name is checked inside action, using "upload" as source if empty
    return {
        "name": [ignore_empty, unicode_safe],
        "storage": [default(shared.config.default_storage()), unicode_safe],
        "upload": [not_missing, files_into_upload],
    }


@validator_args
def file_register(
    default: ValidatorFactory,
    unicode_only: Validator,
    not_missing: Validator,
) -> Schema:
    return {
        "location": [not_missing, unicode_only],
        "storage": [
            default(shared.config.default_storage()),
            unicode_only,
        ],
    }


@validator_args
def file_search(
    unicode_safe: Validator,
    default: ValidatorFactory,
    int_validator: Validator,
    dict_only: Validator,
    convert_to_json_if_string: Validator,
) -> Schema:
    return {
        "start": [default(0), int_validator],
        "rows": [default(10), int_validator],
        "sort": [default("name"), unicode_safe],
        "filters": [default("{}"), convert_to_json_if_string, dict_only],
    }


@validator_args
def file_delete(not_empty: Validator, unicode_safe: Validator) -> Schema:
    return {"id": [not_empty, unicode_safe]}


@validator_args
def file_show(not_empty: Validator, unicode_safe: Validator) -> Schema:
    return {"id": [not_empty, unicode_safe]}


@validator_args
def file_rename(not_empty: Validator, unicode_safe: Validator) -> Schema:
    return {"id": [not_empty, unicode_safe], "name": [not_empty, unicode_safe]}


@validator_args
def transfer_ownership(
    not_empty: Validator,
    boolean_validator: Validator,
    default: ValidatorFactory,
    unicode_safe: Validator,
) -> Schema:
    return {
        "id": [not_empty, unicode_safe],
        "owner_id": [not_empty, unicode_safe],
        "owner_type": [not_empty, unicode_safe],
        "force": [default(False), boolean_validator],
        "pin": [default(False), boolean_validator],
    }


@validator_args
def file_scan(default: ValidatorFactory, unicode_only: Validator, ignore_missing: Validator) -> Schema:
    return {
        "owner_id": [default(""), unicode_only],
        "owner_type": [default("user"), unicode_only],
        "start": [ignore_missing],
        "rows": [ignore_missing],
        "sort": [ignore_missing],
    }


@validator_args
def file_pin(not_empty: Validator, unicode_safe: Validator) -> Schema:
    return {"id": [not_empty, unicode_safe]}


@validator_args
def file_unpin(not_empty: Validator, unicode_safe: Validator) -> Schema:
    return {"id": [not_empty, unicode_safe]}


# not included into CKAN ######################################################


@validator_args
def resource_upload(
    keep_extras: Validator,
    unicode_safe: Validator,
    boolean_validator: Validator,
    ignore_missing: Validator,
) -> Schema:
    return {
        "multipart": [boolean_validator],
        "resource_id": [ignore_missing, unicode_safe],
        "package_id": [ignore_missing, unicode_safe],
        "__extras": [keep_extras],
    }


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
def multipart_start(
    not_empty: Validator,
    unicode_safe: Validator,
    default: ValidatorFactory,
    int_validator: Validator,
    ignore_missing: Validator,
    files_into_upload: Validator,
) -> Schema:
    return {
        "storage": [default(shared.config.default_storage()), unicode_safe],
        "name": [not_empty, unicode_safe],
        "content_type": [not_empty, unicode_safe],
        "size": [not_empty, int_validator],
        "hash": [default(""), unicode_safe],
        "sample": [ignore_missing, files_into_upload],
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
        "keep_plugin_data": [boolean_validator],
    }
