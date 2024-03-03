from ckanext.files.utils import make_collector

_helpers, helper = make_collector()


def get_helpers():
    return dict(_helpers)
