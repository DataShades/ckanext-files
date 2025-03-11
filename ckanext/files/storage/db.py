from __future__ import annotations

import dataclasses
from typing import Any, ClassVar, Iterable

import sqlalchemy as sa

from ckan.model.types import make_uuid

from ckanext.files import shared, types


class DbStorage(shared.Storage):
    hidden = True

    @dataclasses.dataclass()
    class SettingsFactory(shared.Settings):
        db_url: str | None = None
        table: str | None = None
        location_column: str | None = None
        content_column: str | None = None

        _required_options: ClassVar[list[str]] = [
            "db_url",
            "table",
            "location_column",
            "content_column",
        ]

    @classmethod
    def declare_config_options(
        cls,
        declaration: types.Declaration,
        key: types.Key,
    ):
        declaration.declare(key.db_url).required()
        declaration.declare(key.table).required()
        declaration.declare(key.location_column).required()
        declaration.declare(key.content_column).required()

    def __init__(self, settings: Any):
        settings = self.make_settings(settings)
        db_url = settings.db_url

        self.engine = sa.create_engine(db_url)
        self.location_column = sa.column(settings.location_column)
        self.content_column = sa.column(settings.content_column)
        self.table = sa.table(
            settings.table,
            self.location_column,
            self.content_column,
        )

        super().__init__(settings)

    def make_reader(self):
        return DbReader(self)

    def make_uploader(self):
        return DbUploader(self)

    def make_manager(self):
        return DbManager(self)


class DbReader(shared.Reader):
    storage: DbStorage
    capabilities = shared.Capability.STREAM

    def stream(self, data: shared.FileData, extras: dict[str, Any]) -> Iterable[bytes]:
        stmt = (
            sa.select(self.storage.content_column)
            .select_from(self.storage.table)
            .where(self.storage.location_column == data.location)
        )

        row = self.storage.engine.execute(stmt).fetchone()
        if row is None:
            raise shared.exc.MissingFileError(self, data.location)

        return row


class DbUploader(shared.Uploader):
    storage: DbStorage
    capabilities = shared.Capability.CREATE

    def upload(
        self,
        location: str,
        upload: shared.Upload,
        extras: dict[str, Any],
    ) -> shared.FileData:
        uuid = make_uuid()
        reader = upload.hashing_reader()

        values: dict[Any, Any] = {
            self.storage.location_column: uuid,
            self.storage.content_column: reader.read(),
        }
        stmt = sa.insert(self.storage.table, values)

        self.storage.engine.execute(stmt)

        return shared.FileData(
            uuid,
            upload.size,
            upload.content_type,
            reader.get_hash(),
        )


class DbManager(shared.Manager):
    storage: DbStorage
    capabilities = shared.Capability.SCAN | shared.Capability.REMOVE

    def scan(self, extras: dict[str, Any]) -> Iterable[str]:
        stmt = sa.select(self.storage.location_column).select_from(self.storage.table)
        for row in self.storage.engine.execute(stmt):
            yield row[0]

    def remove(
        self,
        data: shared.FileData | shared.MultipartData,
        extras: dict[str, Any],
    ) -> bool:
        stmt = sa.delete(self.storage.table).where(
            self.storage.location_column == data.location,
        )
        self.storage.engine.execute(stmt)
        return True
