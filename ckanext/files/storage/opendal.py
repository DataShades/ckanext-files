from __future__ import annotations

import dataclasses

from file_keeper.default.adapters import opendal as od
from typing_extensions import override

from ckan.config.declaration import Declaration, Key

from ckanext.files import shared


@dataclasses.dataclass()
class Settings(shared.Settings, od.Settings):
    pass


class OpenDalStorage(shared.Storage, od.OpenDalStorage):  # pyright: ignore[reportIncompatibleVariableOverride]
    settings: Settings  # pyright: ignore[reportIncompatibleVariableOverride]
    SettingsFactory = Settings
    ReaderFactory = type("Reader", (shared.Reader, od.Reader), {})
    ManagerFactory = type("Manager", (shared.Manager, od.Manager), {})
    UploaderFactory = type("Uploader", (shared.Uploader, od.Uploader), {})

    @override
    @classmethod
    def declare_config_options(cls, declaration: Declaration, key: Key):
        super().declare_config_options(declaration, key)
        declaration.declare(key.scheme).required().set_description(
            "OpenDAL service type. Check available services at"
            + "  https://docs.rs/opendal/latest/opendal/services/index.html",
        )
        declaration.declare(key.params).set_description(
            "JSON object with parameters passed directly to OpenDAL operator.",
        ).set_validators("default({}) convert_to_json_if_string dict_only")
