# -*- coding: utf-8 -*-

import six

if six.PY3:  # pragma: no cover
    from typing import Any, Callable, TypeVar

    T = TypeVar("T")


def make_collector():
    # type: () -> tuple[dict[str, Any], Callable[[Any], Any]]
    collection = {}

    def collector(fn):
        # type: (T) -> T
        collection[fn.__name__] = fn
        return fn

    return collection, collector
