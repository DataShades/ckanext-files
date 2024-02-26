import ckan.plugins.toolkit as tk

CONF_UNUSED_THRESHOLD = "ckanext.files.unused_threshold"


def get_unused_threshold():
    # type: () -> int
    return tk.asint(tk.config.get(CONF_UNUSED_THRESHOLD))
