import click

from ckanext.files import base, config

__all__ = [
    "files",
]


def get_commands():
    return [files]


@click.group(short_help="ckanext-files CLI commands")
def files():
    pass


@files.group()
def storage():
    """Manage storages."""

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
