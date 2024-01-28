import ckan.plugins.toolkit as tk

CONF_UNUSED_THRESHOLD = "ckanext.files.unused_threshold"


def get_unused_threshold() -> int:
    return tk.config[CONF_UNUSED_THRESHOLD]
