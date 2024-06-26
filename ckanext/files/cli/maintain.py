from __future__ import annotations

import click
import sqlalchemy as sa

import ckan.plugins.toolkit as tk
from ckan import model

from ckanext.files import shared, utils


@click.group()
def group():
    """Storage maintenance."""


storage_option = click.option(
    "-s",
    "--storage-name",
    help="Name of the configured storage",
)


@group.command()
@storage_option
@click.option("--remove", is_flag=True, help="Remove files")
def empty_owner(storage_name: str | None, remove: bool):
    """Manage files that have no owner."""
    storage_name = storage_name or shared.config.default_storage()
    try:
        storage = shared.get_storage(storage_name)
    except shared.exc.UnknownStorageError as err:
        tk.error_shout(err)
        raise click.Abort from err

    if remove and not storage.supports(shared.Capability.REMOVE):
        tk.error_shout(f"Storage {storage_name} does not support file removal")
        raise click.Abort

    stmt = (
        sa.select(shared.File)
        .outerjoin(shared.File.owner_info)
        .where(shared.File.storage == storage_name, shared.Owner.owner_id.is_(None))
    )

    total = model.Session.scalar(sa.select(sa.func.count()).select_from(stmt))
    if not total:
        click.echo(f"Every file in storage {storage_name} has owner reference")
        return
    click.echo("Following files do not have owner reference")

    for file in model.Session.scalars(stmt):
        size = utils.humanize_filesize(file.size)
        click.echo(f"\t{file.id}: {file.name} [{file.content_type}, {size}]")

    if remove and click.confirm("Do you want to delete these files?"):
        action = tk.get_action("files_file_delete")

        with click.progressbar(model.Session.scalars(stmt), length=total) as bar:
            for file in bar:
                action({"ignore_auth": True}, {"id": file.id})


@group.command()
@storage_option
@click.option("--remove", is_flag=True, help="Remove files")
def invalid_owner(storage_name: str | None, remove: bool):
    """Manage files that has suspicious owner reference."""
    storage_name = storage_name or shared.config.default_storage()
    try:
        storage = shared.get_storage(storage_name)
    except shared.exc.UnknownStorageError as err:
        tk.error_shout(err)
        raise click.Abort from err

    if remove and not storage.supports(shared.Capability.REMOVE):
        tk.error_shout(f"Storage {storage_name} does not support file removal")
        raise click.Abort

    stmt = (
        sa.select(shared.File)
        .join(shared.File.owner_info)
        .where(shared.File.storage == storage_name)
    )

    files = [f for f in model.Session.scalars(stmt) if f.owner is None]

    if not files:
        click.echo(
            f"Every owned file in storage {storage_name} has valid owner reference",
        )
        return

    click.echo("Following files have dangling owner reference")
    for file in files:
        size = utils.humanize_filesize(file.size)
        click.echo(
            f"\t{file.id}: {file.name} [{file.content_type}, {size}]. "
            + f"Owner: {file.owner_info.owner_type} {file.owner_info.owner_id}",
        )

    if remove and click.confirm("Do you want to delete these files?"):
        action = tk.get_action("files_file_delete")

        with click.progressbar(files) as bar:
            for file in bar:
                action({"ignore_auth": True}, {"id": file.id})


@group.command()
@storage_option
@click.option("--remove", is_flag=True, help="Remove files")
def missing_files(storage_name: str | None, remove: bool):
    """Manage files that do not exist in storage."""
    storage_name = storage_name or shared.config.default_storage()
    try:
        storage = shared.get_storage(storage_name)
    except shared.exc.UnknownStorageError as err:
        tk.error_shout(err)
        raise click.Abort from err

    if not storage.supports(shared.Capability.EXISTS):
        tk.error_shout(
            f"Storage {storage_name} does not support file availability checks",
        )
        raise click.Abort

    if remove and not storage.supports(shared.Capability.REMOVE):
        tk.error_shout(f"Storage {storage_name} does not support file removal")
        raise click.Abort

    stmt = sa.select(shared.File).where(shared.File.storage == storage_name)
    total = model.Session.scalar(sa.select(sa.func.count()).select_from(stmt))
    missing: list[shared.File] = []
    with click.progressbar(model.Session.scalars(stmt), length=total) as bar:
        for file in bar:
            data = shared.FileData.from_model(file)
            if not storage.exists(data):
                missing.append(file)

    if not missing:
        click.echo(
            f"No missing files located in storage {storage_name}",
        )
        return

    click.echo("Following files are not found in storage")
    for file in missing:
        size = utils.humanize_filesize(file.size)
        click.echo(
            f"\t{file.id}: {file.name} [{file.content_type}, {size}]",
        )

    if remove and click.confirm("Do you want to delete these files?"):
        action = tk.get_action("files_file_delete")

        with click.progressbar(missing) as bar:
            for file in bar:
                action({"ignore_auth": True}, {"id": file.id})
