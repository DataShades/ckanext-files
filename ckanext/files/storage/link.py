from __future__ import annotations

import logging

from file_keeper.default.adapters import link

from ckanext.files import shared

log = logging.getLogger(__name__)


class LinkStorage(shared.Storage, link.LinkStorage):
    hidden = True

    @classmethod
    def declare_config_options(
        cls,
        declaration: shared.types.Declaration,
        key: shared.types.Key,
    ):
        super().declare_config_options(declaration, key)
        declaration.declare_int(key.timeout, 5).set_description(
            "Request timeout used when link details fetched during ANALYZE",
        )
