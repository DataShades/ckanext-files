from __future__ import annotations

import os
import sys
from typing import IO

import click

import ckan.plugins.toolkit as tk
from ckan import model

from ckanext.files import shared


@click.group()
def group():
    """File-level operations."""


@group.command()
@click.argument("file_id")
@click.option("--start", type=int, default=0, help="Start streaming from position")
@click.option("--end", type=int, help="End streaming at position")
@click.option("-o", "--output", help="Stream into specified file or directory")
def stream(file_id: str, output: str | None, start: int, end: int | None):
    """Stream content of the file."""
    file = model.Session.get(shared.File, file_id)
    if not file:
        tk.error_shout("File not found")
        raise click.Abort

    try:
        storage = shared.get_storage(file.storage)
    except shared.exc.UnknownStorageError as err:
        tk.error_shout(err)
        raise click.Abort from err

    if not start and end is None and storage.supports(shared.Capability.STREAM):
        content_stream = storage.stream(shared.FileData.from_object(file))

    elif storage.supports(shared.Capability.RANGE):
        content_stream = storage.range(shared.FileData.from_object(file), start, end)

    elif storage.supports_synthetic(shared.Capability.RANGE, storage):
        content_stream = storage.range_synthetic(shared.FileData.from_object(file), start, end)

    else:
        tk.error_shout("File streaming is not supported")
        raise click.Abort

    if output is None:
        dest: IO[bytes] = sys.stdout.buffer
    else:
        if os.path.isdir(output):
            output = os.path.join(output, file.name)
        dest = open(output, "wb")  # noqa: SIM115

    for chunk in content_stream:
        click.echo(chunk, nl=False, file=dest)
