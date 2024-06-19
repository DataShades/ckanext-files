from __future__ import annotations

import inspect
import pydoc
from typing import Any, Callable

import click

from ckanext.files import shared
from ckanext.files.logic import action


@click.group(hidden=True)
def group():
    """Tools for extension developers."""


@group.command()
def api_docs():
    """Collect and print API documentation."""

    actions = inspect.getmembers(
        action,
        lambda f: inspect.isfunction(f)
        and inspect.getmodule(f) is action
        and not f.__name__.startswith("_"),
    )
    for name, func in actions:
        if not name.startswith("files_"):
            continue
        _doc_function(func)


@group.command()
def shared_docs():
    """Collect and print API documentation."""

    for name in shared.__all__:
        el = getattr(shared, name)
        if inspect.isfunction(el):
            _doc_function(el)


def _doc_function(func: Callable[..., Any]):
    click.echo(f"## `{func.__name__}{inspect.signature(func)}`\n")

    for line in _mdize_doc(func):
        click.echo(line)

    click.echo("\n")


def _mdize_doc(item: Any):
    lines = pydoc.getdoc(item).splitlines()
    in_code_block = False
    for line in lines:
        if line.startswith(">>> ") and not in_code_block:
            in_code_block = True
            yield "```python"

        if not line.startswith(">>>") and in_code_block:
            in_code_block = False
            yield "```"

        yield line[4 if in_code_block else 0 :]

    if in_code_block:
        yield "```"
