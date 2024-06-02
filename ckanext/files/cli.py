from __future__ import annotations

import os
import pydoc
import textwrap

import click

import ckan.plugins.toolkit as tk
from ckan import model

from ckanext.files import base, config, exceptions, shared
from ckanext.files.model import File, Owner

__all__ = [
    "files",
]


@click.group(short_help="ckanext-files CLI commands")
def files():
    pass


@files.command()
@click.argument("file_id")
def stream(file_id: str):
    """Stream content of the file."""
    file = shared.File.get(file_id)
    if not file:
        tk.error_shout("File not found")
        raise click.Abort()

    try:
        storage = shared.get_storage(file.storage)
    except exceptions.UnknownStorageError as err:
        tk.error_shout(err)
        raise click.Abort() from err

    try:
        content_stream = storage.stream(shared.FileData.from_file(file))
    except exceptions.UnsupportedOperationError as err:
        tk.error_shout(err)
        raise click.Abort() from err

    while chunk := content_stream.read(1024 * 256):
        click.echo(chunk, nl=False)


@files.command()
@click.option("-v", "--verbose", is_flag=True, help="Show adapter's documentation")
def adapters(verbose: bool):
    """Show all awailable storage adapters."""
    for name in sorted(base.adapters):
        adapter = base.adapters[name]
        click.secho(
            "{} - {}:{}".format(
                click.style(name, bold=True),
                adapter.__module__,
                adapter.__name__,
            ),
        )
        if verbose:
            doc = pydoc.getdoc(adapter)
            wrapped = textwrap.indent(doc, "\t")
            if wrapped:
                click.echo(wrapped)


@files.command()
@click.option("-v", "--verbose", is_flag=True, help="Show storage's details")
def storages(verbose: bool):
    """Show all configured storages."""
    for name, settings in config.storages().items():
        click.secho("{}: {}".format(click.style(name, bold=True), settings["type"]))
        if verbose:
            storage = shared.get_storage(name)
            click.echo(f"\tSupports: {storage.capabilities}")
            click.echo(f"\tDoes not support: {storage.unsupported_operations()}")


@files.command()
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
    except exceptions.UnsupportedOperationError as err:
        tk.error_shout(err)
        raise click.Abort()  # noqa: B904

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
                data = storage.analyze(name)
            except exceptions.UnsupportedOperationError as err:
                tk.error_shout(err)
                raise click.Abort()  # noqa: B904

            fileobj = File(
                name=os.path.basename(name),
                storage=storage_name,
            )
            data.into_file(fileobj)

            model.Session.add(fileobj)

            if stepfather:
                owner = Owner(
                    item_id=fileobj.id,
                    item_type="file",
                    owner_id=stepfather.id,
                    owner_type="user",
                    access=Owner.ACCESS_FULL,
                )
                model.Session.add(owner)

            model.Session.commit()
