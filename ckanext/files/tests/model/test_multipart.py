from __future__ import annotations

from typing import Any

import pytest
from faker import Faker

from ckan import model

from ckanext.files.model import Multipart, Owner


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestMultipart:
    def test_cascade_owner(self, user: dict[str, Any], faker: Faker):
        multipart = Multipart(
            name=faker.file_name(),
            storage="default",
            location=faker.file_name(),
        )
        owner = Owner(
            item_id=multipart.id,
            item_type="multipart",
            owner_id=user["id"],
            owner_type="user",
        )

        model.Session.add_all([multipart, owner])
        model.Session.commit()
        assert multipart.owner_info is owner
        assert isinstance(multipart.owner, model.User)

        model.Session.delete(owner)
        model.Session.commit()
        model.Session.refresh(multipart)

        assert model.Session.get(Multipart, multipart.id)

        owner = Owner(
            item_id=multipart.id,
            item_type="multipart",
            owner_id=user["id"],
            owner_type="user",
        )
        model.Session.add(owner)
        model.Session.commit()
        model.Session.refresh(multipart)

        assert multipart.owner_info is owner

        model.Session.delete(multipart)
        model.Session.commit()
        assert not model.Session.get(Owner, (owner.item_id, owner.item_type))
