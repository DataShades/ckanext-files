import click

__all__ = [
    "files",
]


def get_commands():
    return [files]


@click.group(short_help="ckanext-files CLI commands")
def files():
    pass
