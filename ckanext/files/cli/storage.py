from __future__ import annotations

import os

import click
import sqlalchemy as sa

import ckan.plugins.toolkit as tk
from ckan import model

from ckanext.files import config, shared
from ckanext.files.model import File, Owner


@click.group()
def group():
    """Storage-level operations."""


@group.command("list")
@click.option("-v", "--verbose", is_flag=True, help="Show storage's details")
def list_storages(verbose: bool):
    """Show all configured storages."""
    for name, settings in config.storages().items():
        click.secho("{}: {}".format(click.style(name, bold=True), settings["type"]))
        if verbose:
            storage = shared.get_storage(name)
            click.echo(f"\tSupports: {storage.capabilities}")
            click.echo(f"\tDoes not support: {~storage.capabilities}")


@group.command()
@click.option("-s", "--storage-name", help="Name of the configured storage")
@click.option(
    "-u",
    "--untracked-only",
    help="Show only untracked files(not recorded in DB)",
    is_flag=True,
)
@click.option(
    "-t",
    "--track",
    help="Track untracked files by creating record in DB",
    is_flag=True,
)
@click.option("-a", "--adopt-by", help="Attach untracked to specified user")
def scan(
    storage_name: str | None,
    untracked_only: bool,
    adopt_by: str | None,
    track: bool,
):
    """Iterate over all files available in storage.

    This command can be used to locate untracked files, that are not registered
    in DB, but exist in storage.

    """
    storage_name = storage_name or config.default_storage()
    storage = shared.get_storage(storage_name)

    try:
        files = storage.scan()
    except shared.exc.UnsupportedOperationError as err:
        tk.error_shout(err)
        raise click.Abort from err

    stepfather = model.User.get(adopt_by)

    for name in files:
        is_untracked = not model.Session.query(
            File.by_location(name, storage_name).exists(),
        ).scalar()

        if untracked_only and not is_untracked:
            continue

        click.echo(name)

        if track and is_untracked:
            try:
                data = storage.analyze(shared.Location(name))
            except shared.exc.UnsupportedOperationError as err:
                tk.error_shout(err)
                raise click.Abort from err

            fileobj = File(
                name=os.path.basename(name),
                storage=storage_name,
            )
            data.into_object(fileobj)

            model.Session.add(fileobj)

            if stepfather:
                owner = Owner(
                    item_id=fileobj.id,
                    item_type="file",
                    owner_id=stepfather.id,
                    owner_type="user",
                )
                model.Session.add(owner)

            model.Session.commit()


@group.command()
@click.argument("src")
@click.argument("dest")
@click.option(
    "-i",
    "--id",
    help="IDs of files for transfer",
    multiple=True,
)
@click.option(
    "-r",
    "--remove",
    help="Remove file from the source after transfer",
    is_flag=True,
)
def transfer(src: str, dest: str, id: tuple[str, ...], remove: bool):
    """Move files between storages."""
    from_storage = shared.get_storage(src)
    to_storage = shared.get_storage(dest)

    is_supported = from_storage.supports_synthetic(
        shared.Capability.MOVE if remove else shared.Capability.COPY, to_storage
    )

    if not is_supported:
        tk.error_shout("Operation is not supported")
        raise click.Abort

    op = from_storage.move_synthetic if remove else from_storage.copy_synthetic

    stmt = sa.select(shared.File).where(shared.File.storage == src)
    if id:
        stmt = stmt.where(shared.File.id.in_(id))

    total = model.Session.scalar(stmt.with_only_columns(sa.func.count()))
    files = model.Session.scalars(stmt)

    with click.progressbar(files, length=total) as bar:
        for item in bar:
            data = shared.FileData.from_object(item)
            new_data = op(data.location, data, to_storage)
            new_data.into_object(item)
            item.storage = dest
            model.Session.commit()
