from __future__ import annotations

import enum
import inspect
import pydoc
from types import ModuleType
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

        _doc_action(func)


@group.command()
def shared_docs():
    """Collect and print API documentation."""

    click.echo(
        """All public utilites are collected inside \
    `ckanext.files.shared` module. Avoid using anything that \
    is not listed there. Do not import anything from modules other than \
    `shared`.""",
    )
    for name in shared.__all__:
        el = getattr(shared, name)

        if inspect.isfunction(el):
            _doc_function(el)

        elif inspect.isclass(el):
            _doc_class(el)

        elif inspect.ismodule(el):
            _doc_module(name, el)


def _doc_action(func: Callable[..., Any]):
    click.echo(f"## {func.__name__}\n")

    for line in _mdize_doc(func):
        click.echo(line)

    click.echo("\n")


def _doc_function(func: Callable[..., Any]):
    click.echo(f"## {func.__name__}\n")

    signature = str(inspect.signature(func)).replace("'", "")
    click.echo(f"Signature: `{signature}`\n")

    for line in _mdize_doc(func):
        click.echo(line)

    click.echo("\n")


def _doc_class(cls: type):
    click.echo(f"## {cls.__name__}\n")
    signature = inspect.signature(cls)

    if signature.parameters and not issubclass(cls, enum.Enum):
        clean_signature = str(signature).replace("''", '""').replace("'", "")
        click.echo(f"Signature: `{clean_signature}`\n")

    for line in _mdize_doc(cls):
        click.echo(line)

    click.echo("\n")


def _doc_module(name: str, module: ModuleType):

    click.echo(f"## {name} ({module.__name__} module)\n")

    for line in _mdize_doc(module):
        click.echo(line)

    click.echo("\n")


def _mdize_doc(item: Any):
    lines = pydoc.getdoc(item).splitlines()
    in_code_block = False
    indent = ""

    for line in lines:
        if line == "Example:":
            yield "!!! example"
            indent = "\t"
            continue

        if line.startswith(">>> ") and not in_code_block:
            in_code_block = True
            yield indent + "```python"

        if not line.startswith(">>>") and in_code_block:
            yield indent + "```"
            in_code_block = False
            indent = ""

        yield indent + line[4 if in_code_block else 0 :]

    if in_code_block:
        yield indent + "```"
