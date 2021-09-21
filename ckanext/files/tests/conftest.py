import pytest

import ckan.model as model
from ckan.cli.db import _resolve_alembic_config


@pytest.fixture
def clean_db(reset_db, monkeypatch):
    reset_db()
    monkeypatch.setattr(
        model.repo, "_alembic_ini", _resolve_alembic_config("files")
    )
    model.repo.upgrade_db()
