from __future__ import annotations

import dataclasses

from file_keeper.default.adapters import sqlalchemy

from ckanext.files import shared, types


@dataclasses.dataclass()
class Settings(shared.Settings, sqlalchemy.Settings):
    pass


class DbStorage(shared.Storage, sqlalchemy.SqlAlchemyStorage):
    hidden = True

    settings: Settings  # type: ignore
    SettingsFactory = Settings

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
