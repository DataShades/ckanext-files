import os

import click

import ckan.plugins.toolkit as tk
from ckan import model

from ckanext.files import base, config, exceptions, shared
from ckanext.files.model import File, Owner

__all__ = [
    "files",
]


def get_commands():
    return [files]


@click.group(short_help="ckanext-files CLI commands")
def files():
    pass


@files.command()
def adapters():
    """Show all awailable storage adapters."""
    for name in sorted(base.adapters):
        adapter = base.adapters.get(name)
        click.secho(
            "{} - {}:{}".format(
                click.style(name, bold=True),
                adapter.__module__,
                adapter.__name__,
            ),
        )


@files.command()
def storages():
    """Show all configured storages."""
    for name, settings in config.storages().items():
        click.secho("{}: {}".format(click.style(name, bold=True), settings["type"]))


@files.command()
@click.option("-s", "--storage-name", help="Name of the configured storage")
@click.option(
    "-o",
    "--orphans-only",
    help="Show only files not registered in DB",
    is_flag=True,
)
@click.option("-m", "--materialize", help="Register orphans in DB", is_flag=True)
@click.option("-a", "--adopt-by", help="Attach orphans to specified user")
def scan(storage_name, orphans_only, adopt_by, materialize):
    # type: (str | None, bool, str | None, bool) -> None
    """Iterate over all files available in storage.

    This command can be used to locate "orphans", that are not registered in
    DB, but exist in storage.

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
        is_orphan = not model.Session.query(
            File.by_location(name, storage_name).exists(),
        ).scalar()

        if orphans_only and not is_orphan:
            continue

        click.echo(name)

        if materialize and is_orphan:
            try:
                data = storage.analyze(name)
            except exceptions.UnsupportedOperationError as err:
                tk.error_shout(err)
                raise click.Abort()  # noqa: B904

            fileobj = File(
                name=os.path.basename(name),
                storage=storage_name,
                storage_data=data,
                completed=True,
            )
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
