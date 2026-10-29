from __future__ import annotations

from typing import Any

import pytest
from click.testing import CliRunner
from faker import Faker

from ckan import model

from ckanext.files.cli import migrate
from ckanext.files.model.file import FilesFile
from ckanext.files.model.owner import FilesOwner
from ckanext.files.model.transfer_history import TransferHistory as FilesTransferHistory

pytestmark = pytest.mark.skipif(not hasattr(model, "File"), reason="core file tables are available from CKAN v2.12")


def legacy_file(user: dict[str, Any], faker: Faker) -> FilesFile:
    """A file, its owner and one ownership transfer, stored in the extension tables."""
    file = FilesFile(name=faker.file_name(), storage="default", location=faker.file_name())
    model.Session.add(file)
    model.Session.flush()

    model.Session.add(FilesOwner(file_id=file.id, owner_id=user["id"], owner_type="user", pinned=True))
    model.Session.flush()

    model.Session.add(FilesTransferHistory(file_id=file.id, owner_id=user["id"], owner_type="user", actor=user["id"]))
    model.Session.commit()
    return file


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestToCoreFiles:
    def test_files_owners_and_history_reach_core_tables(self, user: dict[str, Any], faker: Faker):
        file = legacy_file(user, faker)

        result = CliRunner().invoke(migrate.group, ["to-core-files"])
        assert result.exit_code == 0, result.output

        core = model.Session.get(model.File, file.id)
        assert core
        assert core.location == file.location
        assert core.owner
        assert core.owner.owner_id == user["id"]
        assert core.owner.pinned

        history = model.Session.query(model.FileOwnerTransferHistory).filter_by(file_id=file.id)
        assert history.count() == 1

    def test_running_again_copies_nothing_and_does_not_fail(self, user: dict[str, Any], faker: Faker):
        legacy_file(user, faker)
        runner = CliRunner()

        assert runner.invoke(migrate.group, ["to-core-files"]).exit_code == 0
        again = runner.invoke(migrate.group, ["to-core-files"])

        assert again.exit_code == 0, again.output
        assert "Copied 0 files, 0 owners, 0 transfer history records" in again.output
        assert model.Session.query(model.File).count() == 1

    def test_file_already_in_core_storage_location_is_skipped_with_its_owner(
        self, user: dict[str, Any], faker: Faker
    ):
        file = legacy_file(user, faker)
        model.Session.add(model.File(name="uploaded on 2.12", storage=file.storage, location=file.location))
        model.Session.commit()

        result = CliRunner().invoke(migrate.group, ["to-core-files"])

        assert result.exit_code == 0, result.output
        assert "Copied 0 files, 0 owners, 0 transfer history records" in result.output
        assert model.Session.get(model.File, file.id) is None
