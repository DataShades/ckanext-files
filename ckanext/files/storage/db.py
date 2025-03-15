from __future__ import annotations

from file_keeper.default.adapters import sqlalchemy

from ckanext.files import shared, types


class DbStorage(shared.Storage, sqlalchemy.SqlAlchemyStorage):
    hidden = True

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
