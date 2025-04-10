from __future__ import annotations

import pydoc
import textwrap

import click

from ckanext.files import base

from . import dev, file, maintain, migrate, stats, storage

__all__ = [
    "files",
]


@click.group(short_help="ckanext-files CLI commands")
def files():
    pass


files.add_command(dev.group, "dev")
files.add_command(migrate.group, "migrate")
files.add_command(stats.group, "stats")
files.add_command(storage.group, "storage")
files.add_command(maintain.group, "maintain")
files.add_command(file.group, "file")


@files.command()
@click.option("-v", "--verbose", is_flag=True, help="Show adapter's documentation")
@click.option("-H", "--include-hidden", is_flag=True, help="Show hidden adapters")
def adapters(verbose: bool, include_hidden: bool):
    """Show all awailable storage adapters."""
    for name in sorted(base.adapters):
        adapter = base.adapters[name]
        if adapter.hidden and not include_hidden:
            continue

        click.secho(
            f"{click.style(name, bold=True)} - {adapter.__module__}:{adapter.__name__}",
        )
        if verbose:
            doc = pydoc.getdoc(adapter)
            wrapped = textwrap.indent(doc, "\t")
            if wrapped:
                click.echo(wrapped)
