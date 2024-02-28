import ckanext.files.config as files_conf
from ckanext.files.shared import make_collector


_helpers, helper = make_collector()


def get_helpers():
    return dict(_helpers)


@helper
def files_get_unused_threshold():
    # type: () -> int
    return files_conf.get_unused_threshold()
