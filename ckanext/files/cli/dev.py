from __future__ import annotations

import pydoc

import click

from ckan import authz

from ckanext.files.logic import action


@click.group(hidden=True)
def group():
    """Tools for extension developers."""


@group.command()
def api_docs():
    """Collect and print API documentation."""
    for name, func in authz.get_local_functions(action):
        if not name.startswith("files_"):
            continue

        click.echo(f"## {name}\n")
        click.echo(pydoc.getdoc(func))
