from __future__ import annotations

from typing import Any, Iterable

import click
import sqlalchemy as sa

import ckan.plugins.toolkit as tk
from ckan import model
from ckan.lib.search import rebuild

from ckanext.files import shared


@click.group()
def group():
    """Migrate from original CKAN implementation."""


@group.command("groups")
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
        raise click.Abort

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


@group.command("users")
@click.argument("storage_name")
def migrate_users(storage_name: str):
    """Migrate user avatars to specified storage."""
    content = tk.get_action("files_file_search")(
        {"ignore_auth": True},
        {"storage": storage_name, "rows": 0},
    )
    if not content["count"]:
        tk.error_shout(f"Storage {storage_name} contains 0 files.")
        tk.error_shout("Make sure it points to directory with user images and run:")
        tk.error_shout(f"\tckan files scan -s {storage_name} -t")
        raise click.Abort

    click.echo(f"Found {content['count']} files. Searching file owners...")

    files = tk.get_action("files_file_search")(
        {"ignore_auth": True},
        {"storage": storage_name, "rows": content["count"]},
    )["results"]

    unowned: list[dict[str, Any]] = []
    owned: dict[str, dict[str, Any]] = {}

    bar: Iterable[Any]
    with click.progressbar(files) as bar:
        for info in bar:
            user = model.Session.scalar(
                sa.select(model.User).where(model.User.image_url == info["location"]),
            )

            if user:
                owned[user.id] = info

            else:
                unowned.append(info)

    click.echo(f"Located owners for {len(owned)} files out of {content['count']}.")
    if click.confirm("Show user IDs and corresponding file?"):
        for key, info in owned.items():
            click.echo(f"{key}: {info['location']}")

    if unowned and click.confirm("Show files that do not belong to any user?"):
        for info in unowned:
            click.echo(f"{info['location']}")

    if click.confirm("Transfer file ownership to users identified in previous steps?"):
        with click.progressbar(owned.items()) as bar:
            for user_id, info in bar:
                bar.label = f"Transfering {info['location']}"
                tk.get_action("files_transfer_ownership")(
                    {"ignore_auth": True},
                    {
                        "pin": True,
                        "force": True,
                        "id": info["id"],
                        "owner_type": "user",
                        "owner_id": user_id,
                    },
                )


@group.command("local-resources")
@click.argument("storage_name")
def migrate_local_resources(storage_name: str):  # noqa: C901, PLR0915, PLR0912
    """Migrate resources uploaded via original ResourceUploader."""
    content = tk.get_action("files_file_search")(
        {"ignore_auth": True},
        {"storage": storage_name, "rows": 0},
    )
    if not content["count"]:
        tk.error_shout(f"Storage {storage_name} contains 0 files.")
        tk.error_shout("Make sure it points to directory with user images and run:")
        tk.error_shout(f"\tckan files scan -s {storage_name} -t")
        raise click.Abort

    click.echo(f"Found {content['count']} files. Searching file owners...")

    files = tk.get_action("files_file_search")(
        {"ignore_auth": True},
        {"storage": storage_name, "rows": content["count"]},
    )["results"]

    unowned: list[dict[str, Any]] = []
    owned: dict[str, dict[str, Any]] = {}

    bar: Iterable[Any]
    with click.progressbar(files) as bar:
        for info in bar:
            resource = model.Session.scalar(
                sa.select(model.Resource).where(
                    model.Resource.id == "".join(info["location"].split("/")),
                ),
            )

            if resource:
                owned[resource.id] = info

            else:
                unowned.append(info)

    click.echo(f"Located owners for {len(owned)} files out of {content['count']}.")
    if click.confirm("Show user IDs and corresponding file?"):
        for key, info in owned.items():
            click.echo(f"{key}: {info['location']}")

    if unowned and click.confirm("Show files that do not belong to any user?"):
        for info in unowned:
            click.echo(f"{info['location']}")

    if click.confirm(
        "Transfer file ownership to resources identified in previous steps?",
    ):
        with click.progressbar(owned.items()) as bar:
            for resource_id, info in bar:
                bar.label = f"Transfering {info['location']}"

                tk.get_action("files_transfer_ownership")(
                    {"ignore_auth": True},
                    {
                        "pin": True,
                        "force": True,
                        "id": info["id"],
                        "owner_type": "resource",
                        "owner_id": resource_id,
                    },
                )
    packages: set[str] = set()
    if click.confirm("Modify resources, changing their url_type and url fields?"):
        with click.progressbar(owned.items()) as bar:
            for resource_id, info in bar:
                res = model.Resource.get(resource_id)
                fileobj = model.Session.get(shared.File, info["id"])
                if not fileobj:
                    tk.error_shout(
                        f"Filee {info['id']} disappeared during migration",
                    )
                    raise click.Abort

                if not res:
                    tk.error_shout(
                        f"Resource {resource_id} disappeared during migration",
                    )
                    raise click.Abort

                if not res.package_id:
                    tk.error_shout(f"Resource {resource_id} has no package_id")
                    raise click.Abort

                if res.url_type != "upload":
                    tk.error_shout(
                        f"Resource {resource_id} has suspicious "
                        + f"url_type: {res.url_type}",
                    )
                    raise click.Abort

                res.url_type = "file"
                fileobj.name = res.url
                res.url = info["id"]
                packages.add(res.package_id)

    click.echo("Commit DB changes...")
    model.Session.commit()

    click.echo("Reindex modified packages...")
    for pkg in packages:
        rebuild(pkg)
