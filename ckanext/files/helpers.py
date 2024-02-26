import ckanext.files.config as files_conf


def files_get_unused_threshold():
    # type: () -> int
    return files_conf.get_unused_threshold()
