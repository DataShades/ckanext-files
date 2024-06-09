from __future__ import annotations

from typing import Any

import pytest
from faker import Faker

from ckan import model

from ckanext.files.model import File, Owner


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestFile:
    def test_cascade_owner(self, user: dict[str, Any], faker: Faker):
        file = File(
            name=faker.file_name(),
            storage="default",
            location=faker.file_name(),
        )
        owner = Owner(
            item_id=file.id,
            item_type="file",
            owner_id=user["id"],
            owner_type="user",
        )

        model.Session.add_all([file, owner])
        model.Session.commit()
        assert file.owner_info is owner
        assert isinstance(file.owner, model.User)

        model.Session.delete(owner)
        model.Session.commit()

        assert model.Session.get(File, file.id)

        owner = Owner(
            item_id=file.id,
            item_type="file",
            owner_id=user["id"],
            owner_type="user",
        )
        model.Session.add(owner)
        model.Session.commit()
        model.Session.refresh(file)

        assert file.owner_info is owner

        model.Session.delete(file)
        model.Session.commit()
        assert not model.Session.get(Owner, (owner.item_id, owner.item_type))
