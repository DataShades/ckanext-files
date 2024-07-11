from __future__ import annotations

from datetime import datetime, timezone

import click
import sqlalchemy as sa
from babel.dates import format_datetime, format_timedelta

import ckan.plugins.toolkit as tk
from ckan import model

from ckanext.files import shared, utils


def _now():
    return datetime.now(timezone.utc)


@click.group()
def group():
    """Storage statistics."""


storage_option = click.option(
    "-s",
    "--storage-name",
    help="Name of the configured storage",
)


@group.command()
@storage_option
def overview(storage_name: str | None):
    """General information about storage usage."""
    storage_name = storage_name or shared.config.default_storage()
    stmt = sa.select(
        sa.func.sum(shared.File.size),
        sa.func.count(shared.File.id),
        sa.func.max(shared.File.ctime),
        sa.func.min(shared.File.ctime),
    ).where(shared.File.storage == storage_name)
    row = model.Session.execute(stmt).fetchone()
    size, count, newest, oldest = row if row else (0, 0, _now(), _now())

    if not count:
        tk.error_shout("Storage is not configured or empty")
        raise click.Abort

    click.secho(f"Number of files: {click.style(count, bold=True)}")
    click.secho(
        f"Used space: {click.style(utils.humanize_filesize(size), bold=True)}",
    )
    click.secho(
        "Newest file created at: "
        + f"{click.style(format_datetime(newest), bold=True)} "
        + f"({format_timedelta(newest - _now(), add_direction=True)})",
    )
    click.secho(
        "Oldest file created at: "
        + f"{click.style(format_datetime(oldest), bold=True)} "
        + f"({format_timedelta(oldest - _now(), add_direction=True)})",
    )


@group.command()
@storage_option
def types(storage_name: str | None):
    """Files distribution by MIMEtype."""
    storage_name = storage_name or shared.config.default_storage()
    stmt = (
        sa.select(
            shared.File.content_type,
            sa.func.count(shared.File.content_type).label("count"),
        )
        .where(shared.File.storage == storage_name)
        .group_by(shared.File.content_type)
        .order_by(shared.File.content_type)
    )

    total = model.Session.scalar(sa.select(sa.func.sum(stmt.c.count)))
    click.secho(
        f"Storage {click.style(storage_name, bold=True)} contains "
        + f"{click.style(total, bold=True)} files",
    )
    for content_type, count in model.Session.execute(stmt):
        click.secho(f"\t{content_type}: {click.style(count, bold=True)}")


@group.command()
@storage_option
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Show distribution for every owner ID",
)
def owner(storage_name: str | None, verbose: bool):
    """Files distribution by owner."""
    storage_name = storage_name or shared.config.default_storage()
    owner_col = (
        sa.func.concat(shared.Owner.owner_type, " ", shared.Owner.owner_id)
        if verbose
        else sa.func.concat(shared.Owner.owner_type, "")
    )

    stmt = (
        sa.select(
            owner_col.label("owner"),
            sa.func.count(shared.File.id),
        )
        .where(shared.File.storage == storage_name)
        .outerjoin(
            shared.Owner,
            sa.and_(
                shared.Owner.item_id == shared.File.id,
                shared.Owner.item_type == "file",
            ),
        )
        .group_by(owner_col)
    ).order_by(owner_col)

    total = model.Session.scalar(sa.select(sa.func.sum(stmt.c.count)))
    click.secho(
        f"Storage {click.style(storage_name, bold=True)} contains "
        + f"{click.style(total, bold=True)} files",
    )
    for owner, count in model.Session.execute(stmt):
        clean_owner = owner.strip() or click.style(
            "has no owner",
            underline=True,
            bold=True,
        )
        click.secho(
            f"\t{clean_owner}: {click.style(count, bold=True)}",
        )
