import ckan.plugins.toolkit as tk
from ckan.logic.schema import validator_args


CONFIG_KIND = "ckanext.files.default.kind"
DEFAULT_KIND = "ckanext_files_file"


@validator_args
def file_create(
        ignore_empty, dict_only, not_empty, unicode_safe, default, ignore, not_missing
):
    default_kind = tk.config.get(CONFIG_KIND, DEFAULT_KIND)
    return {
        "name": [not_empty, unicode_safe],
        "upload": [not_missing],
        "kind": [default(default_kind), unicode_safe],
        "extras": [ignore_empty, dict_only],
        "__extras": [ignore],
    }


@validator_args
def file_update(not_empty, ignore_missing, unicode_safe, dict_only, ignore):
    return {
        "id": [not_empty],
        "name": [ignore_missing, unicode_safe],
        "upload": [ignore_missing],
        "kind": [ignore_missing, unicode_safe],
        "extras": [ignore_missing, dict_only],
        "__extras": [ignore],
    }
