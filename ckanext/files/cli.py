from __future__ import annotations

import os
import pydoc
import textwrap
from typing import Any, Iterable

import click
import sqlalchemy as sa

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
    file = model.Session.get(shared.File, file_id)
    if not file:
        tk.error_shout("File not found")
        raise click.Abort

    try:
        storage = shared.get_storage(file.storage)
    except exceptions.UnknownStorageError as err:
        tk.error_shout(err)
        raise click.Abort from err

    try:
        content_stream = storage.stream(shared.FileData.from_model(file))
    except exceptions.UnsupportedOperationError as err:
        tk.error_shout(err)
        raise click.Abort from err

    while chunk := content_stream.read(1024 * 256):
        click.echo(chunk, nl=False)


@files.command()
@click.option("-v", "--verbose", is_flag=True, help="Show adapter's documentation")
def adapters(verbose: bool):
    """Show all awailable storage adapters."""
    for name in sorted(base.adapters):
        adapter = base.adapters[name]
        if adapter.hidden:
            continue

        click.secho(
            f"{click.style(name, bold=True)} - {adapter.__module__}:{adapter.__name__}",
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
                data = storage.analyze(name)
            except exceptions.UnsupportedOperationError as err:
                tk.error_shout(err)
                raise click.Abort from err

            fileobj = File(
                name=os.path.basename(name),
                storage=storage_name,
            )
            data.into_model(fileobj)

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


@files.group()
def migrate():
    """Migrate from original CKAN implementation."""


@migrate.command("groups")
@click.argument("storage_name")
def migrate_groups(storage_name: str):
    """Migrate group images to specified storage."""
    content = tk.get_action("files_file_search")(
        {"ignore_auth": True},
        {"storage": storage_name, "rows": 0},
    )
    if not content["count"]:
        tk.error_shout(f"Storage {storage_name} contains 0 files.")
        tk.error_shout("Make sure it points to directory with group images and run:")
        tk.error_shout(f"\tckan files scan -s {storage_name} -t")

    click.echo(f"Found {content['count']} files. Searching file owners...")

    files = tk.get_action("files_file_search")(
        {"ignore_auth": True},
        {"storage": storage_name, "rows": content["count"]},
    )["results"]

    unowned: list[dict[str, Any]] = []
    owned: dict[tuple[str, bool], dict[str, Any]] = {}

    bar: Iterable[Any]
    with click.progressbar(files) as bar:
        for info in bar:
            group = model.Session.scalar(
                sa.select(model.Group).where(model.Group.image_url == info["location"]),
            )

            if group:
                owned[(group.id, group.is_organization)] = info
            else:
                unowned.append(info)
            unowned.append(info)
    click.echo(f"Located owners for {len(owned)} files out of {content['count']}.")
    if click.confirm("Show group IDs and corresponding file?"):
        for key, info in owned.items():
            click.echo(f"{key[0]}: {info['location']}")

    if unowned and click.confirm("Show files that do not belong to any group?"):
        for info in unowned:
            click.echo(f"{info['location']}")

    if click.confirm("Transfer file ownership to group identified in previous steps?"):
        with click.progressbar(owned.items()) as bar:
            for key, info in bar:
                group_id, is_organization = key
                bar.label = f"Transfering {info['location']}"
                tk.get_action("files_transfer_ownership")(
                    {"ignore_auth": True},
                    {
                        "pin": True,
                        "force": True,
                        "id": info["id"],
                        "owner_type": "organization" if is_organization else "group",
                        "owner_id": group_id,
                    },
                )


@migrate.command("update-group-image-url")
@click.argument("storage_name")
def update_group_images(storage_name: str):
    """Migrate group images to specified storage."""
    user = tk.get_action("get_site_user")({"ignore_auth": True}, {})
    content = tk.get_action("files_file_search")(
        {"ignore_auth": True},
        {"storage": storage_name, "rows": 0},
    )
    files = tk.get_action("files_file_search")(
        {"ignore_auth": True},
        {"storage": storage_name, "rows": content["count"]},
    )["results"]

    bar: Iterable[Any]
    with click.progressbar(files) as bar:
        for info in bar:
            group = model.Session.scalar(
                sa.select(model.Group).where(model.Group.image_url == info["location"]),
            )
            if group:
                bar.label = f"Patching group {group.id}"
                tk.get_action(
                    "organization_patch" if group.is_organization else "group_patch",
                )(
                    {"ignore_auth": True, "user": user["name"]},
                    {"id": group.id, "image_url": info["id"]},
                )


@migrate.command("users")
@click.argument("storage_name")
def migrate_users(storage_name: str):
    """Migrate user avatars to specified storage."""


@migrate.command("local-resources")
@click.argument("storage_name")
def migrate_local_resources(storage_name: str):
    """Migrate resources uploaded via original ResourceUploader."""
