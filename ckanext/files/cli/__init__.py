from __future__ import annotations

import pydoc
import textwrap

import click

from ckan.config.declaration import Declaration, Key

from ckanext.files import base

from . import dev, file, maintain, migrate, stats, storage

try:
    import ckan.cli.files  # type: ignore # noqa

    entrypoint = "ex-files"
except ImportError:
    entrypoint = "files"


__all__ = [
    "files",
]


@click.group(entrypoint, short_help="ckanext-files CLI commands")
def files():
    pass


files.add_command(dev.group, "dev")
files.add_command(migrate.group, "migrate")
files.add_command(stats.group, "stats")
files.add_command(storage.group, "storage")
files.add_command(maintain.group, "maintain")
files.add_command(file.group, "file")


@files.command()
@click.option("-c", "--with-configuration", is_flag=True, help="Show adapter's configuration")
@click.option("-d", "--with-docs", is_flag=True, help="Show adapter's documentation")
@click.option("-H", "--include-hidden", is_flag=True, help="Show hidden adapters")
@click.argument("adapter", required=False)
def adapters(
    adapter: str | None,
    with_docs: bool,
    include_hidden: bool,
    with_configuration: bool,
):
    """Show all awailable storage adapters."""
    for name in sorted(base.adapters):
        if adapter and name != adapter:
            continue

        item = base.adapters[name]
        if item.hidden and not include_hidden:
            continue

        click.secho(
            f"{click.style(name, bold=True)} - {item.__module__}:{item.__name__}",
        )

        if with_docs and (doc := pydoc.getdoc(item)):
            doc = f"{click.style('Documentation:', bold=True)}\n{doc}"
            wrapped = textwrap.indent(doc, "\t")
            click.secho(wrapped)
            click.echo()

        if with_configuration and issubclass(item, base.Storage):
            decl = Declaration()
            item.declare_config_options(decl, Key.from_string("ckanext.files.storage.NAME"))
            configuration = decl.into_ini(False, True)
            configuration = f"{click.style('Configuration:', bold=True)}\n{configuration}"
            wrapped = textwrap.indent(configuration, "\t")
            click.secho(wrapped)
            click.echo()
