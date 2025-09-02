from __future__ import annotations

import dataclasses

from file_keeper.default.adapters import sqlalchemy
from typing_extensions import override

from ckanext.files import shared, types


@dataclasses.dataclass()
class Settings(shared.Settings, sqlalchemy.Settings):
    pass


class DbStorage(shared.Storage, sqlalchemy.SqlAlchemyStorage):  # pyright: ignore[reportIncompatibleVariableOverride]
    hidden = True

    settings: Settings  # pyright: ignore[reportIncompatibleVariableOverride]
    SettingsFactory = Settings
    ReaderFactory = type("Reader", (shared.Reader, sqlalchemy.Reader), {})
    ManagerFactory = type("Manager", (shared.Manager, sqlalchemy.Manager), {})
    UploaderFactory = type("Uploader", (shared.Uploader, sqlalchemy.Uploader), {})

    @override
    @classmethod
    def declare_config_options(
        cls,
        declaration: types.Declaration,
        key: types.Key,
    ):
        declaration.declare(key.db_url).required()
        declaration.declare(key.table_name).required()
        declaration.declare(key.location_column).required()
        declaration.declare(key.content_column).required()
