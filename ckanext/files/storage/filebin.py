from __future__ import annotations

from file_keeper.default.adapters import filebin

from ckan.config.declaration import Declaration, Key

from ckanext.files import shared


class FilebinStorage(shared.Storage, filebin.FilebinStorage):
    hidden = True

    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        super().declare_config_options(declaration, key)

        declaration.declare(key.bin).required().set_description("ID of the bin")
        declaration.declare_int(key.timeout, 10).set_description(
            "Timeout of requests to filebin.net",
        )
